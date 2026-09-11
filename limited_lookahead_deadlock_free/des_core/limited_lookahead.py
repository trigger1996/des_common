from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations

from des_core.automata import DFA, Event, State
from des_core.deadlock_semantics import is_concrete_deadlock
from des_core.partial_observation import observable_successors, unobservable_closure


ControlPattern = frozenset[Event]
Belief = frozenset[State]


@dataclass(frozen=True)
class LocalLookaheadStats:
    belief: Belief
    lookahead_states: frozenset[State]
    good_patterns: int
    bad_patterns: int
    pending_patterns: int

    @property
    def local_pair_count(self) -> int:
        return self.good_patterns + self.bad_patterns + self.pending_patterns


@dataclass(frozen=True)
class ExampleLookaheadReport:
    name: str
    state_count: int
    event_count: int
    belief_count: int
    control_pattern_count: int
    global_belief_upper_bound: int
    global_pair_upper_bound: int
    local_reports: tuple[LocalLookaheadStats, ...]

    @property
    def max_local_states(self) -> int:
        return max((len(report.lookahead_states) for report in self.local_reports), default=0)

    @property
    def max_local_pairs(self) -> int:
        return max((report.local_pair_count for report in self.local_reports), default=0)

    @property
    def total_local_pairs(self) -> int:
        return sum(report.local_pair_count for report in self.local_reports)


def admissible_control_patterns(plant: DFA) -> tuple[ControlPattern, ...]:
    controllable = sorted(plant.controllable)
    uncontrollable = frozenset(plant.uncontrollable)
    patterns: list[ControlPattern] = []
    for size in range(len(controllable) + 1):
        for subset in combinations(controllable, size):
            patterns.append(frozenset(subset) | uncontrollable)
    return tuple(sorted(patterns, key=lambda item: (len(item), sorted(item))))


def post_leq(plant: DFA, seeds: Belief, horizon: int) -> frozenset[State]:
    """Return the local window with the initial belief as layer one.

    A horizon of ``u`` contains paths with fewer than ``u`` events.  Thus a
    state first reached after exactly ``u`` events is outside the window.  This
    is the LL-BTS convention used for the D -> O -> D construction: an
    observable transition at the boundary cannot create a successor D-state.
    """
    reached: set[State] = set(seeds)
    queue: deque[tuple[State, int]] = deque((state, 0) for state in seeds)
    while queue:
        state, depth = queue.popleft()
        if depth >= horizon - 1:
            continue
        for _event, target in plant.enabled(state):
            if target in reached:
                continue
            reached.add(target)
            queue.append((target, depth + 1))
    return frozenset(reached)


def controlled_unobservable_reach(
    plant: DFA,
    seeds: Belief,
    control_pattern: ControlPattern,
    lookahead_states: frozenset[State],
) -> frozenset[State]:
    reached: set[State] = set(seeds) & set(lookahead_states)
    queue: deque[State] = deque(reached)
    while queue:
        state = queue.popleft()
        for event, target in plant.enabled(state):
            if event not in control_pattern or event in plant.observable:
                continue
            if target not in lookahead_states or target in reached:
                continue
            reached.add(target)
            queue.append(target)
    return frozenset(reached)


def classify_control_pattern(
    plant: DFA,
    belief: Belief,
    lookahead_states: frozenset[State],
    control_pattern: ControlPattern,
) -> str:
    tail = controlled_unobservable_reach(plant, belief, control_pattern, lookahead_states)
    if any(is_concrete_deadlock(plant, state) for state in tail):
        return "bad"
    if tail and all(
        any(
            event in control_pattern and target in lookahead_states
            for event, target in plant.enabled(state)
        )
        for state in tail
    ):
        return "good"
    return "pending"


def reachable_beliefs(plant: DFA) -> tuple[Belief, ...]:
    initial = unobservable_closure(plant, {plant.initial}, plant.observable)
    queue: deque[Belief] = deque([initial])
    visited: set[Belief] = set()
    while queue:
        belief = queue.popleft()
        if belief in visited:
            continue
        visited.add(belief)
        for successor in observable_successors(plant, belief, plant.observable):
            if successor.closed_belief not in visited and successor.closed_belief not in queue:
                queue.append(successor.closed_belief)
    return tuple(sorted(visited, key=lambda item: (len(item), sorted(item))))


def analyze_local_lookahead(example_name: str, plant: DFA, horizon: int) -> ExampleLookaheadReport:
    patterns = admissible_control_patterns(plant)
    reports: list[LocalLookaheadStats] = []
    for belief in reachable_beliefs(plant):
        lookahead_states = post_leq(plant, belief, horizon)
        counts = {"good": 0, "bad": 0, "pending": 0}
        for pattern in patterns:
            counts[classify_control_pattern(plant, belief, lookahead_states, pattern)] += 1
        reports.append(
            LocalLookaheadStats(
                belief=belief,
                lookahead_states=lookahead_states,
                good_patterns=counts["good"],
                bad_patterns=counts["bad"],
                pending_patterns=counts["pending"],
            )
        )
    global_belief_upper_bound = 2 ** len(plant.states)
    global_pair_upper_bound = global_belief_upper_bound * len(patterns)
    return ExampleLookaheadReport(
        name=example_name,
        state_count=len(plant.states),
        event_count=len(plant.events),
        belief_count=len(reports),
        control_pattern_count=len(patterns),
        global_belief_upper_bound=global_belief_upper_bound,
        global_pair_upper_bound=global_pair_upper_bound,
        local_reports=tuple(reports),
    )
