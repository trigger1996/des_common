from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
from functools import cache

from des_core.automata import DFA, Event, State
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
    edges: frozenset[tuple[str, str, str, str]]
    edge_count: int
    lookahead_states: frozenset[State]
    decision_estimate_states: frozenset[State]
    observation_estimate_states: frozenset[State]
    searched_states: frozenset[State]
    maximal_good_patterns: tuple[ControlPattern, ...]


def admissible_control_patterns(plant: DFA) -> tuple[ControlPattern, ...]:
    controllable = sorted(plant.controllable)
    patterns: list[ControlPattern] = []
    for size in range(len(controllable) + 1):
        for subset in combinations(controllable, size):
            patterns.append(frozenset(subset))
    return tuple(sorted(patterns, key=lambda item: (len(item), sorted(item))))


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
) -> LLBTSResult:
    lookahead_states = post_leq(plant, frozenset({current_state}), horizon)
    # Per-construction memoization: x_L and the plant are fixed for this call.
    # Keep all paper-defined (root, estimate) nodes and their transitions.
    estimates: dict[Estimate, Estimate] = {}

    def intern(estimate: Estimate) -> Estimate:
        return estimates.setdefault(estimate, estimate)

    @cache
    def estimate_tag(estimate: Estimate) -> str:
        return _estimate_tag(plant, estimate, lookahead_states)

    @cache
    def unobservable_reach(estimate: Estimate, pattern: ControlPattern) -> Estimate:
        return intern(controlled_unobservable_reach(plant, estimate, pattern, lookahead_states))

    @cache
    def next_estimate(estimate: Estimate, event: Event) -> Estimate:
        return intern(observable_next(plant, estimate, event, lookahead_states))

    patterns = admissible_control_patterns(plant)
    initial: DecisionState = (current_state, intern(frozenset({current_state})))
    decision_states: set[DecisionState] = {initial}
    observation_states: set[ObservationState] = set()
    edges: set[tuple[str, str, str, str]] = set()
    edge_count = 0
    observation_edge_counts: dict[ObservationState, int] = {}
    frontier: deque[DecisionState] = deque([initial])
    expanded: set[DecisionState] = set()
    initial_good_patterns: set[ControlPattern] = set()

    while frontier:
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

        for pattern in patterns:
            observation_estimate = unobservable_reach(decision_estimate, pattern)
            observation: ObservationState = (observation_estimate, pattern)
            observation_states.add(observation)
            edge_count += 1
            observation_label = (
                observation_state_label(plant, observation, lookahead_states)
                if store_edges
                else ""
            )
            if store_edges:
                edges.add((decision_label, observation_label, _pattern_label(pattern), "control"))

            if decision == initial and estimate_tag(observation[0]) == "Y":
                initial_good_patterns.add(pattern)
            if estimate_tag(observation[0]) == "N":
                continue

            # An existing O node has the same outgoing transitions for every
            # incoming D. The paper merges O nodes and adds edges only if new.
            # Preserve the legacy edge_count (which includes repeated visits).
            if observation in observation_edge_counts:
                edge_count += observation_edge_counts[observation]
                continue
            before_observable_edges = edge_count
            for event in sorted(plant.observable & _enabled_events(plant, pattern)):
                successor_estimate = next_estimate(observation_estimate, event)
                if not successor_estimate:
                    continue
                for successor_root in sorted(successor_estimate):
                    successor: DecisionState = (successor_root, successor_estimate)
                    is_new = successor not in decision_states
                    decision_states.add(successor)
                    edge_count += 1
                    if store_edges:
                        successor_label = decision_state_label(plant, successor, lookahead_states)
                        edges.add((observation_label, successor_label, event, "observable"))
                    if is_new and estimate_tag(successor[1]) != "N":
                        frontier.append(successor)
            observation_edge_counts[observation] = edge_count - before_observable_edges

    decision_estimate_states = frozenset(
        state
        for estimate in {estimate for _root, estimate in decision_states}
        for state in estimate
    )
    observation_estimate_states = frozenset(
        state
        for estimate, _pattern in observation_states
        for state in estimate
    )
    searched_states = decision_estimate_states | observation_estimate_states
    return LLBTSResult(
        decision_states=frozenset(decision_states),
        observation_states=frozenset(observation_states),
        edges=frozenset(edges),
        edge_count=edge_count,
        lookahead_states=lookahead_states,
        decision_estimate_states=decision_estimate_states,
        observation_estimate_states=observation_estimate_states,
        searched_states=searched_states,
        maximal_good_patterns=_maximal_patterns(initial_good_patterns),
    )


def make_ll_bts_synthesis_snapshots(
    plant: DFA,
    horizon: int,
) -> list[BeliefStateSynthesisSnapshot]:
    lookahead_states = post_leq(plant, frozenset({plant.initial}), horizon)
    patterns = admissible_control_patterns(plant)
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
            observation_estimate = controlled_unobservable_reach(
                plant, decision_estimate, pattern, lookahead_states
            )
            observation: ObservationState = (observation_estimate, pattern)
            stage_observations.add(observation)
            all_observations.add(observation)
            searched_states.update(observation_estimate)
            observation_label = observation_state_label(plant, observation, lookahead_states)
            stage_edges.add((decision_label, observation_label, _pattern_label(pattern), "control"))
            all_edges.add((decision_label, observation_label, _pattern_label(pattern), "control"))

            observation_tag = _observation_tag(plant, observation, lookahead_states)
            if decision == initial and observation_tag == "Y":
                initial_good_patterns.add(pattern)
            if observation_tag == "N":
                bad_observations += 1
                continue
            if _is_inconsistent_observation(plant, observation):
                inconsistent_observations += 1

            for event in sorted(plant.observable & _enabled_events(plant, pattern)):
                successor_estimate = observable_next(
                    plant, observation_estimate, event, lookahead_states
                )
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
        edges = {(decision_label, observation_label, _pattern_label(pattern), "control")}
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
            edges.add((successor_label, next_observation_label, _pattern_label(pattern), "control"))

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
    return f"O({_estimate_label(estimate)},{_pattern_label(pattern)})"


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
    estimate, pattern = observation
    enabled_events = _enabled_events(plant, pattern)
    return bool(estimate) and any(
        not any(event in enabled_events for event, _target in plant.enabled(state))
        for state in estimate
    )


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


def _maximal_patterns(patterns: set[ControlPattern]) -> tuple[ControlPattern, ...]:
    maximal = [
        pattern
        for pattern in patterns
        if not any(pattern < other for other in patterns)
    ]
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
