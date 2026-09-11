"""Algorithm 2: prune the constructed LL-BTS before advancing the online run."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace

from des_core.automata import DFA, Event, State
from des_core.ll_bts import (
    ControlPattern, Estimate, LLBTSResult, ObservationState, _maximal_patterns,
)


@dataclass(frozen=True)
class LLBTSControlResult:
    # Empty means there is no retained structure rooted at the current decision.
    empty: bool
    maximal_patterns: tuple[ControlPattern, ...]
    forward_successors: tuple[tuple[ControlPattern, Event, State], ...]


def solve_ll_bts(plant, current, horizon, *, pattern_mode="factored",
                 expansion_progress=None, use_certificate=True):
    """Return an exact initial synthesis and the structure used to prove it.

    A consistent substructure permitting the full controllable alphabet proves
    the unique largest initial pattern: every other pattern is its subset.
    If this sufficient certificate fails, compute the complete factored graph.
    This never uses a failed certificate as evidence of an empty synthesis.
    The certificate's node/edge counts describe its substructure, not the full
    LL-BTS; construct_ll_bts remains the full-construction API.
    """
    from des_core.ll_bts import construct_ll_bts
    if horizon < 0:
        raise ValueError("horizon must be nonnegative")
    attempted = use_certificate and pattern_mode == "factored"
    if attempted:
        from des_core.compact_ll_bts import construct_compact
        from des_core.limited_lookahead import post_leq
        window = post_leq(plant, frozenset({current}), horizon)
        result = construct_compact(plant, current, window, expansion_progress,
                                   maximal_hidden_only=True)
        control = synthesize_ll_bts_controls(plant, current, result)
        if not control.empty and plant.controllable in control.maximal_patterns:
            return replace(result, construction_strategy="maximal_pattern_certificate"), control
        # Release the failed trial before the potentially larger complete solve.
        del result, control
    result = construct_ll_bts(plant, current, horizon, False,
                              expansion_progress, pattern_mode=pattern_mode)
    control = synthesize_ll_bts_controls(plant, current, result)
    if attempted:
        result = replace(result, construction_strategy="full_after_certificate", synthesis_passes=2)
    return result, control


def synthesize_ll_bts_controls(
    plant: DFA, current: State, result: LLBTSResult,
) -> LLBTSControlResult:
    """Apply Definition deadlock_free_consistent and Algorithm 2.

    Algorithm 1 has already constructed the D->O relation. Algorithm 2 therefore
    reuses ``result.control_choices`` and performs only classification/pruning.
    The implementation groups O-state calculations by their estimate whenever
    the paper-defined result is independent of gamma; this does not alter the
    retained LL-BTS or the maximally permissive patterns.
    """
    if result.pattern_mode == "factored":
        from des_core.factored_synthesis import synthesize_factored_controls
        return synthesize_factored_controls(plant, current, result)
    window = result.lookahead_states
    adjacency = {q: tuple(plant.enabled(q)) for q in window}
    observable = plant.observable
    uncontrollable = plant.uncontrollable
    uncontrollable_observable = uncontrollable & observable
    deadlocks = {q for q, edges in adjacency.items() if not edges}

    # Internal bit masks make the repeated "does gamma enable at least one of
    # these controllable events?" test O(1). The public ControlPattern remains
    # the paper-aligned frozenset representation.
    controllable_order = tuple(sorted(plant.controllable))
    control_bit = {event: 1 << index for index, event in enumerate(controllable_order)}
    pattern_mask = {
        pattern: sum(control_bit[event] for event in pattern)
        for pattern in {obs_pattern for _estimate, obs_pattern in result.observation_states}
    }

    estimates = frozenset(estimate for _root, estimate in result.decision_states)
    observations = result.observation_states
    canonical = {estimate: estimate for estimate in estimates}

    # Reverse relations required by the backward fixed point. Lists are enough:
    # each D-estimate -> O relation is unique in control_choices, and each O is
    # added at most once per successor estimate below.
    incoming_controls: dict[ObservationState, list[Estimate]] = defaultdict(list)
    incoming_observations: dict[Estimate, list[ObservationState]] = defaultdict(list)

    bad_decisions = {estimate for estimate in estimates if not estimate.isdisjoint(deadlocks)}
    bad_observations: set[ObservationState] = set()

    # Number of currently surviving O choices per D-estimate. Keeping counts
    # avoids copying every large frozenset of choices into another mutable set.
    remaining_choices: dict[Estimate, int] = {}
    for estimate in estimates:
        if estimate in bad_decisions:
            remaining_choices[estimate] = 0
            continue
        options = result.control_choices.get(estimate, ())
        remaining_choices[estimate] = len(options)
        for observation in options:
            incoming_controls[observation].append(estimate)

    # Analyze each distinct O-estimate once.  NX_sigma(x), the set of observable
    # events present at x, and the per-state consistency requirements depend on x
    # but not on the rest of gamma.
    estimate_analysis: dict[
        Estimate,
        tuple[
            dict[Event, Estimate],          # local NX_sigma(x) intersect x_L
            frozenset[Event],               # observable events occurring from x
            tuple[int, ...],                # retained for cache shape compatibility
        ],
    ] = {}

    def analyze_estimate(estimate: Estimate):
        cached = estimate_analysis.get(estimate)
        if cached is not None:
            return cached

        targets: dict[Event, set[State]] = defaultdict(set)
        observable_occurs: set[Event] = set()
        raw_requirements: set[int] = set()

        for state in estimate:
            outgoing = adjacency[state]
            for event, target in outgoing:
                if event not in observable:
                    continue
                observable_occurs.add(event)
                if target in window:
                    targets[event].add(target)

        local_targets = {
            event: canonical.get(frozenset(states), frozenset(states))
            for event, states in targets.items()
        }
        # If A is a subset of B, requiring gamma to hit A already implies
        # that it hits B. Keep only inclusion-minimal requirement masks.
        if 0 in raw_requirements:
            requirements = (0,)
        else:
            ordered_requirements = sorted(raw_requirements, key=int.bit_count)
            minimal_requirements: list[int] = []
            for requirement in ordered_requirements:
                if any((existing & requirement) == existing for existing in minimal_requirements):
                    continue
                minimal_requirements.append(requirement)
            requirements = tuple(minimal_requirements)

        cached = (
            local_targets,
            frozenset(observable_occurs),
            requirements,
        )
        estimate_analysis[estimate] = cached
        return cached

    enabled_observable_cache: dict[ControlPattern, frozenset[Event]] = {}

    def enabled_observable(pattern: ControlPattern) -> frozenset[Event]:
        cached = enabled_observable_cache.get(pattern)
        if cached is None:
            cached = frozenset((pattern & observable) | uncontrollable_observable)
            enabled_observable_cache[pattern] = cached
        return cached

    for observation in observations:
        estimate, pattern = observation
        local_targets, observable_occurs, requirements = analyze_estimate(estimate)
        enabled_obs = enabled_observable(pattern)

        local_enabled_events = local_targets.keys() & enabled_obs

        invalid = (
            not estimate
            or not estimate.isdisjoint(deadlocks)
        )
        if invalid:
            bad_observations.add(observation)
            continue

        # Build O -> successor-D reverse edges only for observations that are not
        # already known bad. Multiple observable events may yield the same
        # successor estimate; Algorithm 2 needs that predecessor only once.
        seen_successors: set[Estimate] = set()
        for event in local_enabled_events:
            successor = local_targets[event]
            if successor in seen_successors:
                continue
            seen_successors.add(successor)
            if successor not in estimates:
                bad_observations.add(observation)
                break
            incoming_observations[successor].append(observation)

    # Any D with no available control choice is bad before the recursive pass.
    for estimate, count in remaining_choices.items():
        if count == 0:
            bad_decisions.add(estimate)

    queue = deque(
        [("D", estimate) for estimate in bad_decisions]
        + [("O", observation) for observation in bad_observations]
    )

    # Backward fixed point: losing O removes one D choice; losing D invalidates
    # every predecessor O because the environment can force that O->D outcome.
    while queue:
        kind, node = queue.popleft()
        if kind == "D":
            for observation in incoming_observations.get(node, ()):
                if observation not in bad_observations:
                    bad_observations.add(observation)
                    queue.append(("O", observation))
            continue

        for estimate in incoming_controls.get(node, ()):
            if estimate in bad_decisions:
                continue
            remaining_choices[estimate] -= 1
            if remaining_choices[estimate] == 0:
                bad_decisions.add(estimate)
                queue.append(("D", estimate))

    initial = frozenset({current})
    if initial not in estimates or initial in bad_decisions:
        return LLBTSControlResult(True, (), ())

    surviving_initial = tuple(
        observation
        for observation in result.control_choices.get(initial, ())
        if observation not in bad_observations
    )
    patterns = _maximal_patterns(pattern for _estimate, pattern in surviving_initial)
    maximal_set = frozenset(patterns)

    forward = set()
    for observation in surviving_initial:
        estimate, pattern = observation
        if pattern not in maximal_set:
            continue
        local_targets, _observable_occurs, _requirements = analyze_estimate(estimate)
        for event in local_targets.keys() & enabled_observable(pattern):
            successor = local_targets[event]
            for root in successor:
                forward.add((pattern, event, root))

    return LLBTSControlResult(
        False,
        patterns,
        tuple(
            sorted(
                forward,
                key=lambda item: (len(item[0]), sorted(item[0]), item[1], item[2]),
            )
        ),
    )

