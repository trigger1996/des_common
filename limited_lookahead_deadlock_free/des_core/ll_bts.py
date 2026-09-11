from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
from functools import cache
from typing import Callable

from des_core.automata import DFA, Event, State
from des_core.control_reduction import representative_choices
from des_core.deadlock import BeliefStateSynthesisSnapshot
from des_core.deadlock_semantics import is_concrete_deadlock
from des_core.limited_lookahead import post_leq


ControlPattern = frozenset[Event]
Estimate = frozenset[State]
DecisionState = tuple[State, Estimate]
ObservationState = tuple[Estimate, ControlPattern]


@dataclass(frozen=True)
class LLBTSResult:
    decision_states: frozenset[DecisionState]
    observation_states: frozenset[ObservationState]
    # D-estimate -> O-state choices already computed during LL-BTS construction.
    # Algorithm 2 reuses this relation instead of recomputing UR(x, gamma).
    control_choices: dict[Estimate, tuple[ObservationState, ...]]
    edges: frozenset[tuple[str, str, str, str]]
    edge_count: int
    lookahead_states: frozenset[State]
    decision_estimate_states: frozenset[State]
    observation_estimate_states: frozenset[State]
    searched_states: frozenset[State]
    maximal_good_patterns: tuple[ControlPattern, ...]
    # In factored mode an O=(x, upper_pattern) denotes an observable-choice
    # family, not the single concrete pattern upper_pattern. Use Algorithm 2
    # to obtain executable patterns; never execute a raw family upper bound.
    pattern_mode: str = "explicit"
    _compact_graph: object | None = None
    construction_strategy: str = "full"
    synthesis_passes: int = 1


@cache
def _control_patterns_from_events(controllable: tuple[Event, ...]) -> tuple[ControlPattern, ...]:
    """Enumerate compact control decisions once per controllable alphabet.

    Internally a pattern stores only the controllable events selected by the
    supervisor.  The paper's full admissible pattern is recovered as
    ``pattern | Sigma_uc``.  This is an exact encoding because uncontrollable
    events are mandatory in every admissible pattern.
    """
    patterns: list[ControlPattern] = []
    for size in range(len(controllable) + 1):
        for subset in combinations(controllable, size):
            patterns.append(frozenset(subset))
    return tuple(patterns)


def admissible_control_patterns(plant: DFA) -> tuple[ControlPattern, ...]:
    return _control_patterns_from_events(tuple(sorted(plant.controllable)))


def controlled_unobservable_reach(
    plant: DFA,
    seeds: Estimate,
    control_pattern: ControlPattern,
    lookahead_states: frozenset[State],
) -> Estimate:
    enabled_events = _enabled_events(plant, control_pattern)
    reached = set(seeds) & set(lookahead_states)
    queue: deque[State] = deque(reached)
    while queue:
        source = queue.popleft()
        for event, target in plant.enabled(source):
            if event in plant.observable or event not in enabled_events:
                continue
            if target not in lookahead_states or target in reached:
                continue
            reached.add(target)
            queue.append(target)
    return frozenset(reached)


def observable_next(
    plant: DFA,
    estimate: Estimate,
    event: Event,
    lookahead_states: frozenset[State],
) -> Estimate:
    return frozenset(
        target
        for state in estimate
        for enabled_event, target in plant.enabled(state)
        if enabled_event == event and target in lookahead_states
    )


def construct_ll_bts(
    plant: DFA,
    current_state: State,
    horizon: int,
    store_edges: bool = True,
    expansion_progress: Callable[[int, int, int], None] | None = None,
    *, pattern_mode: str = "explicit",
) -> LLBTSResult:
    """Construct Algorithm 1's current-window LL-BTS.

    The optimizations below are representation/cache optimizations only:
    * equal decision estimates share D->O computations because delta_DO depends
      on (estimate, gamma, x_L), not on the concrete root;
    * UR is memoized by the enabled controllable-unobservable part of gamma,
      because observable controllable events cannot change an unobservable reach;
    * O->D successors are expanded once per merged observation state.

    In explicit mode all paper-defined nodes and transitions are retained.
    Reduced mode retains maximal behavior-equivalent representatives; Algorithm
    2 returns the same maximal patterns and observable physical successors.
    Counts in reduced mode describe the represented graph, not the full graph.
    Factored mode additionally represents all observable subsets as one family;
    synthesize_ll_bts_controls resolves that family by the same backward fixed
    point. Locally decidable inconsistent families are pruned before expansion.
    Raw family upper bounds are not synthesized executable controls.
    """
    if pattern_mode not in {"explicit", "reduced", "factored"}:
        raise ValueError("pattern_mode must be explicit, reduced or factored")
    if horizon < 0:
        raise ValueError("horizon must be nonnegative")
    lookahead_states = post_leq(plant, frozenset({current_state}), horizon)
    if pattern_mode == "factored" and not store_edges:
        from des_core.compact_ll_bts import construct_compact
        return construct_compact(plant, current_state, lookahead_states, expansion_progress)

    # Per-construction interning. x_L and plant are fixed for this call.
    estimates: dict[Estimate, Estimate] = {}

    def intern(estimate: Estimate) -> Estimate:
        return estimates.setdefault(estimate, estimate)

    adjacency = {state: tuple(plant.enabled(state)) for state in lookahead_states}
    observable = plant.observable
    uncontrollable = plant.uncontrollable
    uncontrollable_unobservable = plant.unobservable & uncontrollable
    controllable_unobservable = plant.unobservable & plant.controllable

    # A state with no plant successor is a concrete deadlock. A state whose only
    # successors leave x_L is a horizon-boundary state, not a concrete deadlock.
    deadlocks = frozenset(state for state, targets in adjacency.items() if not targets)
    interior = frozenset(
        state for state, targets in adjacency.items()
        if any(target in lookahead_states for _event, target in targets)
    )
    unobservable_adjacency = {
        state: tuple(
            (event, target)
            for event, target in targets
            if event not in observable and target in lookahead_states
        )
        for state, targets in adjacency.items()
    }

    @cache
    def estimate_tag(estimate: Estimate) -> str:
        if not estimate.isdisjoint(deadlocks):
            return "N"
        return "Y" if estimate and estimate <= interior else "U"

    # UR only depends on controllable-unobservable choices. Uncontrollable
    # unobservable events are always enabled; observable events never belong to UR.
    @cache
    def unobservable_reach_by_hidden_choice(
        estimate: Estimate,
        hidden_choice: ControlPattern,
    ) -> Estimate:
        enabled_hidden = hidden_choice | uncontrollable_unobservable
        reached = set(estimate)
        queue = deque(estimate)
        while queue:
            source = queue.popleft()
            for event, target in unobservable_adjacency[source]:
                if event in enabled_hidden and target not in reached:
                    reached.add(target)
                    queue.append(target)
        return intern(frozenset(reached))

    @cache
    def observable_successors(estimate: Estimate) -> dict[Event, Estimate]:
        # Compute all NX_sigma(x) intersect x_L in one traversal. The selected
        # gamma later filters which observable sigma are enabled.
        targets_by_event: dict[Event, set[State]] = {}
        for state in estimate:
            for event, target in adjacency[state]:
                if event in observable and target in lookahead_states:
                    targets_by_event.setdefault(event, set()).add(target)
        return {
            event: intern(frozenset(targets))
            for event, targets in targets_by_event.items()
        }

    patterns = admissible_control_patterns(plant) if pattern_mode == "explicit" else ()
    # Precompute the two parts of gamma used in the hot loops.
    pattern_data = tuple(
        (
            pattern,
            frozenset(pattern & controllable_unobservable),
            frozenset((pattern | uncontrollable) & observable),
        )
        for pattern in patterns
    )

    initial: DecisionState = (current_state, intern(frozenset({current_state})))
    decision_states: set[DecisionState] = {initial}
    observation_states: set[ObservationState] = set()

    # D-estimate -> ordered O choices. Equal estimates have the same D->O map
    # within one fixed x_L, even when carried by several concrete roots.
    control_choices_work: dict[Estimate, tuple[ObservationState, ...]] = {}

    edges: set[tuple[str, str, str, str]] = set()
    edge_count = 0
    frontier: deque[DecisionState] = deque([initial])
    expanded: set[DecisionState] = set()
    initial_good_patterns: set[ControlPattern] = set()

    if expansion_progress is not None:
        expansion_progress(len(decision_states), len(observation_states), len(frontier))

    while frontier:
        if expansion_progress is not None and len(expanded) % 256 == 0:
            expansion_progress(len(decision_states), len(observation_states), len(frontier))

        decision = frontier.popleft()
        if decision in expanded or estimate_tag(decision[1]) == "N":
            continue
        expanded.add(decision)
        _root, decision_estimate = decision
        decision_label = (
            decision_state_label(plant, decision, lookahead_states)
            if store_edges
            else ""
        )

        # If another concrete root already carried the same estimate, Algorithm 1
        # has exactly the same O choices and O->D successors for this D-state.
        # Reuse them; still retain/count this D-state's own D->O transitions.
        reused_choices = control_choices_work.get(decision_estimate)
        if reused_choices is not None:
            edge_count += len(reused_choices)
            if store_edges:
                for observation in reused_choices:
                    edges.add(
                        (
                            decision_label,
                            observation_state_label(plant, observation, lookahead_states),
                            _pattern_label(observation[1]),
                            "control",
                        )
                    )
            continue

        choices_for_estimate: list[ObservationState] = []

        if pattern_mode in {"reduced", "factored"}:
            local_choices = representative_choices(
                plant, decision_estimate, lookahead_states, adjacency,
                factor_observable=pattern_mode == "factored",
            )
        else:
            local_choices = (
                (unobservable_reach_by_hidden_choice(decision_estimate, hidden_choice), pattern)
                for pattern, hidden_choice, _enabled_observable in pattern_data
            )
        for observation_estimate, pattern in local_choices:
            observation_estimate = intern(observation_estimate)
            enabled_observable = (pattern | uncontrollable) & observable
            observation: ObservationState = (observation_estimate, pattern)
            choices_for_estimate.append(observation)
            is_new_observation = observation not in observation_states
            observation_states.add(observation)

            # Every expanded D-state has one D->O edge for every admissible gamma.
            edge_count += 1
            observation_label = (
                observation_state_label(plant, observation, lookahead_states)
                if store_edges
                else ""
            )
            if store_edges:
                edges.add(
                    (decision_label, observation_label, _pattern_label(_enabled_events(plant, pattern)), "control")
                )

            if decision == initial and estimate_tag(observation_estimate) == "Y":
                initial_good_patterns.add(pattern)
            if estimate_tag(observation_estimate) == "N":
                continue

            # Observation states are merged by (estimate, gamma). Their outgoing
            # O->D transitions are therefore constructed exactly once.
            if not is_new_observation:
                continue

            successors_by_event = observable_successors(observation_estimate)
            for event in sorted(enabled_observable):
                successor_estimate = successors_by_event.get(event)
                if not successor_estimate:
                    continue
                for successor_root in sorted(successor_estimate):
                    successor: DecisionState = (successor_root, successor_estimate)
                    is_new = successor not in decision_states
                    decision_states.add(successor)
                    edge_count += 1
                    if store_edges:
                        successor_label = decision_state_label(
                            plant, successor, lookahead_states
                        )
                        edges.add(
                            (observation_label, successor_label, event, "observable")
                        )
                    if is_new and estimate_tag(successor_estimate) != "N":
                        frontier.append(successor)

        control_choices_work[decision_estimate] = tuple(choices_for_estimate)

    if expansion_progress is not None:
        expansion_progress(len(decision_states), len(observation_states), 0)

    decision_estimates = {estimate for _root, estimate in decision_states}
    observation_estimates = {estimate for estimate, _pattern in observation_states}
    decision_estimate_states = frozenset(
        state for estimate in decision_estimates for state in estimate
    )
    observation_estimate_states = frozenset(
        state for estimate in observation_estimates for state in estimate
    )
    searched_states = decision_estimate_states | observation_estimate_states

    return LLBTSResult(
        decision_states=frozenset(decision_states),
        observation_states=frozenset(observation_states),
        control_choices=dict(control_choices_work),
        edges=frozenset(edges),
        edge_count=edge_count,
        lookahead_states=lookahead_states,
        decision_estimate_states=decision_estimate_states,
        observation_estimate_states=observation_estimate_states,
        searched_states=searched_states,
        maximal_good_patterns=_maximal_patterns(initial_good_patterns),
        pattern_mode=pattern_mode,
    )


def make_ll_bts_synthesis_snapshots(
    plant: DFA,
    horizon: int,
) -> list[BeliefStateSynthesisSnapshot]:
    lookahead_states = post_leq(plant, frozenset({plant.initial}), horizon)
    patterns = admissible_control_patterns(plant)
    controllable_unobservable = plant.controllable & plant.unobservable
    enabled_observable_by_pattern = {
        pattern: frozenset((pattern | plant.uncontrollable) & plant.observable)
        for pattern in patterns
    }

    @cache
    def snapshot_ur(estimate: Estimate, hidden_choice: ControlPattern) -> Estimate:
        return controlled_unobservable_reach(
            plant, estimate, hidden_choice, lookahead_states
        )

    @cache
    def snapshot_nx(estimate: Estimate, event: Event) -> Estimate:
        return observable_next(plant, estimate, event, lookahead_states)

    initial: DecisionState = (plant.initial, frozenset({plant.initial}))
    decision_states: set[DecisionState] = {initial}
    frontier: deque[DecisionState] = deque([initial])
    expanded: set[DecisionState] = set()
    searched_states: set[State] = set(initial[1])
    initial_good_patterns: set[ControlPattern] = set()
    snapshots: list[BeliefStateSynthesisSnapshot] = []
    recent_stages: deque[tuple[frozenset[State], frozenset[tuple[str, str, str, str]]]] = deque(maxlen=2)
    all_observations: set[ObservationState] = set()
    all_edges: set[tuple[str, str, str, str]] = set()

    def capture(
        title: str,
        current: DecisionState | None,
        stage_observations: set[ObservationState],
        stage_edges: set[tuple[str, str, str, str]],
    ) -> None:
        decision_labels = set()
        if current is not None:
            decision_labels.add(decision_state_label(plant, current, lookahead_states))
        observation_labels = {
            observation_state_label(plant, state, lookahead_states)
            for state in stage_observations
        }
        edge_nodes = {
            node
            for source, target, _event, _kind in stage_edges
            for node in (source, target)
        }
        nodes = decision_labels | observation_labels | edge_nodes
        no_nodes = _tagged_ll_bts_labels(plant, decision_states, stage_observations, lookahead_states, "N")
        inconsistent_nodes = _inconsistent_observation_labels(plant, stage_observations, lookahead_states)
        show_history = len(snapshots) < 5
        faded_nodes = (
            frozenset(
                node
                for previous_nodes, _previous_edges in recent_stages
                for node in previous_nodes
                if node not in nodes
            )
            if show_history
            else frozenset()
        )
        faded_edges = (
            frozenset(
                edge
                for _previous_nodes, previous_edges in recent_stages
                for edge in previous_edges
                if edge not in stage_edges
            )
            if show_history
            else frozenset()
        )
        snapshots.append(
            BeliefStateSynthesisSnapshot(
                title=title,
                known_nodes=frozenset(nodes),
                known_edges=frozenset(stage_edges),
                current=(
                    decision_state_label(plant, current, lookahead_states)
                    if current is not None
                    else None
                ),
                frontier=frozenset(
                    decision_state_label(plant, state, lookahead_states)
                    for state in frontier
                ),
                yes=frozenset(),
                no=frozenset(nodes & no_nodes),
                unknown=frozenset(nodes & inconsistent_nodes),
                closed_beliefs=frozenset(nodes),
                raw_beliefs=frozenset(),
                deadlock=frozenset(),
                layout_aliases=tuple(),
                faded_nodes=faded_nodes,
                faded_edges=faded_edges,
                layout_style="chain",
                label_style="compact",
            )
        )
        recent_stages.append((frozenset(nodes), frozenset(stage_edges)))

    capture(
        f"stage 0: initialize LL-BTS; u={horizon}; |x_L|={len(lookahead_states)}",
        initial,
        set(),
        set(),
    )

    stage = 0
    while frontier:
        decision = frontier.popleft()
        if decision in expanded:
            continue
        if _decision_tag(plant, decision, lookahead_states) == "N":
            stage += 1
            capture(f"stage {stage}: cut off bad decision state", decision, set(), set())
            continue

        expanded.add(decision)
        _root, decision_estimate = decision
        decision_label = decision_state_label(plant, decision, lookahead_states)
        stage_observations: set[ObservationState] = set()
        stage_edges: set[tuple[str, str, str, str]] = set()
        added_successors = 0
        bad_observations = 0
        bad_successors = 0
        inconsistent_observations = 0

        for pattern in patterns:
            observation_estimate = snapshot_ur(
                decision_estimate, frozenset(pattern & controllable_unobservable)
            )
            observation: ObservationState = (observation_estimate, pattern)
            stage_observations.add(observation)
            all_observations.add(observation)
            searched_states.update(observation_estimate)
            observation_label = observation_state_label(plant, observation, lookahead_states)
            stage_edges.add((decision_label, observation_label, _pattern_label(_enabled_events(plant, pattern)), "control"))
            all_edges.add((decision_label, observation_label, _pattern_label(_enabled_events(plant, pattern)), "control"))

            observation_tag = _observation_tag(plant, observation, lookahead_states)
            if decision == initial and observation_tag == "Y":
                initial_good_patterns.add(pattern)
            if observation_tag == "N":
                bad_observations += 1
            if _is_inconsistent_observation(plant, observation):
                inconsistent_observations += 1

            for event in sorted(enabled_observable_by_pattern[pattern]):
                successor_estimate = snapshot_nx(observation_estimate, event)
                if not successor_estimate:
                    continue
                searched_states.update(successor_estimate)
                for successor_root in sorted(successor_estimate):
                    successor: DecisionState = (successor_root, successor_estimate)
                    if successor not in decision_states:
                        added_successors += 1
                    decision_states.add(successor)
                    successor_label = decision_state_label(plant, successor, lookahead_states)
                    stage_edges.add((observation_label, successor_label, event, "observable"))
                    all_edges.add((observation_label, successor_label, event, "observable"))
                    successor_tag = _decision_tag(plant, successor, lookahead_states)
                    if successor_tag == "N":
                        bad_successors += 1
                    if successor not in expanded and successor_tag != "N":
                        frontier.append(successor)

        stage += 1
        choices = ", ".join(_pattern_label(pattern) for pattern in _maximal_patterns(initial_good_patterns)) or "<none>"
        capture(
            (
                f"stage {stage}: expand {decision_label}; "
                f"observations={len(stage_observations)}, new decisions={added_successors}, "
                f"bad observations={bad_observations}, bad successors={bad_successors}, "
                f"inconsistent observations={inconsistent_observations}, "
                f"|Q_t|={len(searched_states)}, choices={choices}"
            ),
            decision,
            stage_observations,
            stage_edges,
        )

    capture(
        f"stage {stage + 1}: complete single-step synthesis; |Q_t|={len(searched_states)}",
        initial,
        all_observations,
        all_edges,
    )
    return snapshots


def make_ll_bts_chain_snapshots(
    plant: DFA,
    horizon: int,
    successor_limit: int = 4,
) -> list[BeliefStateSynthesisSnapshot]:
    lookahead_states = post_leq(plant, frozenset({plant.initial}), horizon)
    pattern = frozenset(plant.events)
    initial: DecisionState = (plant.initial, frozenset({plant.initial}))
    frontier: deque[DecisionState] = deque([initial])
    expanded: set[DecisionState] = set()
    snapshots: list[BeliefStateSynthesisSnapshot] = []
    stage = 0

    while frontier:
        decision = frontier.popleft()
        if decision in expanded or _decision_tag(plant, decision, lookahead_states) == "N":
            continue
        expanded.add(decision)

        decision_label = decision_state_label(plant, decision, lookahead_states)
        observation = (
            controlled_unobservable_reach(plant, decision[1], pattern, lookahead_states),
            pattern,
        )
        observation_label = observation_state_label(plant, observation, lookahead_states)
        nodes = {decision_label, observation_label}
        edges = {(decision_label, observation_label, _pattern_label(_enabled_events(plant, pattern)), "control")}
        successor_decisions: list[DecisionState] = []

        if _observation_tag(plant, observation, lookahead_states) != "N":
            for event in sorted(plant.observable & _enabled_events(plant, pattern)):
                successor_estimate = observable_next(
                    plant, observation[0], event, lookahead_states
                )
                if not successor_estimate:
                    continue
                for successor_root in sorted(successor_estimate):
                    successor = (successor_root, successor_estimate)
                    successor_decisions.append(successor)
                    successor_label = decision_state_label(plant, successor, lookahead_states)
                    nodes.add(successor_label)
                    edges.add((observation_label, successor_label, event, "observable"))
                    if successor not in expanded and _decision_tag(plant, successor, lookahead_states) != "N":
                        frontier.append(successor)

        for successor in successor_decisions[:successor_limit]:
            if _decision_tag(plant, successor, lookahead_states) == "N":
                continue
            successor_label = decision_state_label(plant, successor, lookahead_states)
            next_observation = (
                controlled_unobservable_reach(plant, successor[1], pattern, lookahead_states),
                pattern,
            )
            next_observation_label = observation_state_label(
                plant, next_observation, lookahead_states
            )
            nodes.add(next_observation_label)
            edges.add((successor_label, next_observation_label, _pattern_label(_enabled_events(plant, pattern)), "control"))

        snapshots.append(
            BeliefStateSynthesisSnapshot(
                title=(
                    f"chain stage {stage}: {decision_label} -> O -> D -> O preview; "
                    f"u={horizon}, pattern={_pattern_label(pattern)}"
                ),
                known_nodes=frozenset(nodes),
                known_edges=frozenset(edges),
                current=decision_label,
                frontier=frozenset(
                    decision_state_label(plant, state, lookahead_states)
                    for state in frontier
                ),
                yes=frozenset(),
                no=frozenset(),
                unknown=frozenset(),
                closed_beliefs=frozenset(nodes),
                raw_beliefs=frozenset(),
                deadlock=frozenset(),
                layout_aliases=tuple(),
                layout_style="chain",
                label_style="compact",
            )
        )
        stage += 1

    if not snapshots:
        decision_label = decision_state_label(plant, initial, lookahead_states)
        snapshots.append(
            BeliefStateSynthesisSnapshot(
                title=f"chain stage 0: no nonbad decision can be expanded; u={horizon}",
                known_nodes=frozenset({decision_label}),
                known_edges=frozenset(),
                current=decision_label,
                frontier=frozenset(),
                yes=frozenset(),
                no=frozenset(),
                unknown=frozenset(),
                closed_beliefs=frozenset({decision_label}),
                raw_beliefs=frozenset(),
                deadlock=frozenset(),
                layout_aliases=tuple(),
                layout_style="chain",
                label_style="compact",
            )
        )
    return snapshots


def make_ll_bts_transition_report(
    plant: DFA,
    horizon: int,
    selected_stages: tuple[int, ...] | None = None,
) -> str:
    snapshots = make_ll_bts_synthesis_snapshots(plant, horizon)
    chain_snapshots = make_ll_bts_chain_snapshots(plant, horizon)
    if selected_stages is None:
        selected_stages = _default_report_stages(snapshots)

    lines = [
        f"LL-BTS transition report",
        f"initial: {plant.initial}",
        f"observable: {sorted(plant.observable)}",
        f"unobservable: {sorted(plant.unobservable)}",
        f"lookahead limit u: {horizon}",
        "",
        "Selected synthesis stages",
    ]
    for stage in selected_stages:
        if stage < 0 or stage >= len(snapshots):
            continue
        lines.extend(_snapshot_report_lines(stage, snapshots[stage]))

    lines.append("")
    lines.append("Selected chain-view stages")
    for stage in selected_stages:
        if stage < 0 or stage >= len(chain_snapshots):
            continue
        lines.extend(_snapshot_report_lines(stage, chain_snapshots[stage]))

    return "\n".join(lines) + "\n"


def _default_report_stages(snapshots: list[BeliefStateSynthesisSnapshot]) -> tuple[int, ...]:
    candidates = {0, 1, 2, 3, 5, 8, len(snapshots) - 2, len(snapshots) - 1}
    for index, snapshot in enumerate(snapshots):
        text = " ".join(sorted(snapshot.known_nodes)) + " " + snapshot.title
        if any(token in text for token in ("q_4", "q_5", "q_15", "q_16", "q_17")):
            candidates.add(index)
    return tuple(sorted(stage for stage in candidates if 0 <= stage < len(snapshots)))


def _tagged_ll_bts_labels(
    plant: DFA,
    decision_states: set[DecisionState],
    observation_states: set[ObservationState],
    lookahead_states: frozenset[State],
    tag: str,
) -> set[str]:
    labels = {
        decision_state_label(plant, decision, lookahead_states)
        for decision in decision_states
        if _decision_tag(plant, decision, lookahead_states) == tag
    }
    labels.update(
        observation_state_label(plant, observation, lookahead_states)
        for observation in observation_states
        if _observation_tag(plant, observation, lookahead_states) == tag
    )
    return labels


def _inconsistent_observation_labels(
    plant: DFA,
    observation_states: set[ObservationState],
    lookahead_states: frozenset[State],
) -> set[str]:
    return {
        observation_state_label(plant, observation, lookahead_states)
        for observation in observation_states
        if _is_inconsistent_observation(plant, observation)
    }


def _snapshot_report_lines(index: int, snapshot: BeliefStateSynthesisSnapshot) -> list[str]:
    nodes = sorted(snapshot.known_nodes)
    decisions = [node for node in nodes if node.startswith("D(")]
    observations = [node for node in nodes if node.startswith("O(")]
    control_edges = sorted(edge for edge in snapshot.known_edges if edge[3] == "control")
    observable_edges = sorted(edge for edge in snapshot.known_edges if edge[3] == "observable")
    lines = [
        "",
        f"[stage {index}] {snapshot.title}",
        f"current: {snapshot.current or '<none>'}",
        f"decision states ({len(decisions)}):",
    ]
    lines.extend(f"  {node}" for node in decisions)
    lines.append(f"observation states ({len(observations)}):")
    lines.extend(f"  {node}" for node in observations)
    lines.append(f"control edges D->O ({len(control_edges)}):")
    lines.extend(
        f"  {source} --{event}--> {target}"
        for source, target, event, _kind in control_edges[:12]
    )
    if len(control_edges) > 12:
        lines.append(f"  ... {len(control_edges) - 12} more")
    lines.append(f"observable edges O->D ({len(observable_edges)}):")
    lines.extend(
        f"  {source} --{event}--> {target}"
        for source, target, event, _kind in observable_edges[:16]
    )
    if len(observable_edges) > 16:
        lines.append(f"  ... {len(observable_edges) - 16} more")
    frontier = ", ".join(sorted(snapshot.frontier)) if snapshot.frontier else "<empty>"
    lines.append(f"frontier: {frontier}")
    return lines


def decision_state_label(
    plant: DFA,
    decision: DecisionState,
    lookahead_states: frozenset[State],
) -> str:
    root, estimate = decision
    return f"D({_state_label(root)},{_estimate_label(estimate)})"


def observation_state_label(
    plant: DFA,
    observation: ObservationState,
    lookahead_states: frozenset[State],
) -> str:
    estimate, pattern = observation
    return f"O({_estimate_label(estimate)},{_pattern_label(_enabled_events(plant, pattern))})"


def _decision_tag(
    plant: DFA,
    decision: DecisionState,
    lookahead_states: frozenset[State],
) -> str:
    _root, estimate = decision
    return _estimate_tag(plant, estimate, lookahead_states)


def _observation_tag(
    plant: DFA,
    observation: ObservationState,
    lookahead_states: frozenset[State],
) -> str:
    estimate, _pattern = observation
    return _estimate_tag(plant, estimate, lookahead_states)


def _is_inconsistent_observation(
    plant: DFA,
    observation: ObservationState,
) -> bool:
    """An O-state's consistency is a graph property, not a local deadlock test.

    Definition of consistency used here:
    (1) for an observation state, every permitted observable NX successor
    inside the local window must be represented by an O -> D edge; an estimate
    state with no permitted observable successor creates no requirement; and
    (2) for a decision state, at least one D -> O control choice, including
    ``emptyset union Sigma_uo``, must remain.  The latter is checked while
    pruning the bipartite graph.  In particular, disabling every local event
    at a state does not by itself make an O-state inconsistent.
    """
    return False


def _estimate_tag(
    plant: DFA,
    estimate: Estimate,
    lookahead_states: frozenset[State],
) -> str:
    if any(is_concrete_deadlock(plant, state) for state in estimate):
        return "N"
    if estimate and all(
        any(target in lookahead_states for _event, target in plant.enabled(state))
        for state in estimate
    ):
        return "Y"
    return "U"


def _maximal_patterns(patterns) -> tuple[ControlPattern, ...]:
    """Return inclusion-maximal patterns without the quadratic full scan."""
    ordered = sorted(set(patterns), key=lambda item: (-len(item), tuple(sorted(item))))
    maximal: list[ControlPattern] = []
    for pattern in ordered:
        # Longer patterns are visited first.  If one already retained pattern
        # contains this pattern, it cannot be maximal.
        if any(pattern < other for other in maximal):
            continue
        maximal.append(pattern)
    return tuple(sorted(maximal, key=lambda item: (len(item), sorted(item))))


def _enabled_events(plant: DFA, pattern: ControlPattern) -> frozenset[Event]:
    return pattern | plant.uncontrollable


def _estimate_label(estimate: Estimate) -> str:
    return "{" + ",".join(_state_label(state) for state in sorted(estimate, key=_state_label)) + "}"


def _state_label(state: State) -> str:
    if isinstance(state, tuple):
        return "(" + ",".join(str(item) for item in state) + ")"
    return str(state)


def _pattern_label(pattern: ControlPattern) -> str:
    return "{" + ",".join(sorted(pattern)) + "}"
