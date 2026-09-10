from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from des_core.automata import DFA, Event, State


@dataclass(frozen=True)
class ObservableSuccessor:
    event: Event
    raw_targets: frozenset[State]
    closed_belief: frozenset[State]


def unobservable_closure(
    plant: DFA,
    seeds: set[State] | frozenset[State],
    observable: frozenset[Event],
) -> frozenset[State]:
    closure = set(seeds)
    queue: deque[State] = deque(seeds)
    while queue:
        state = queue.popleft()
        for event, target in plant.enabled(state):
            if event in observable or target in closure:
                continue
            closure.add(target)
            queue.append(target)
    return frozenset(closure)


def observable_successors(
    plant: DFA,
    closed_belief: frozenset[State],
    observable: frozenset[Event],
) -> list[ObservableSuccessor]:
    successors: list[ObservableSuccessor] = []
    observable_events = sorted(
        {
            event
            for state in closed_belief
            for event, _target in plant.enabled(state)
            if event in observable
        }
    )
    for event in observable_events:
        raw_targets = frozenset(
            target
            for state in closed_belief
            for enabled_event, target in plant.enabled(state)
            if enabled_event == event
        )
        successors.append(
            ObservableSuccessor(
                event=event,
                raw_targets=raw_targets,
                closed_belief=unobservable_closure(plant, raw_targets, observable),
            )
        )
    return successors
