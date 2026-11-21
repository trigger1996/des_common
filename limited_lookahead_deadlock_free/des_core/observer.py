from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from enum import Enum

from des_core.automata import DESExample, DFA, State
from des_core.partial_observation import observable_successors, unobservable_closure


class ObservationTag(Enum):
    YES = "Y"
    NO = "N"
    UNKNOWN = "U"


@dataclass(frozen=True)
class TaggedObserverState:
    """Observer state i = (X, tag), where X is a belief over plant states."""

    belief: frozenset[State]
    tag: ObservationTag

    @property
    def label(self) -> State:
        return tagged_belief_name(self.belief, self.tag)


def build_partial_observation_example(
    base: DESExample,
    observable: frozenset[str],
) -> DESExample:
    observer = build_observer_dfa(base.dfa, observable)
    observed_plant = replace(base.dfa, observable=observable)

    return DESExample(
        name=f"{base.name}_partial_observation",
        dfa=observer,
        layout=_observer_layout(observer),
        description=(
            f"Partial-observation observer for {base.name}. "
            f"Observable events: {sorted(observable)}. "
            "States are belief sets after unobservable closure."
        ),
        lookahead_limit=base.lookahead_limit,
        source_name=base.name,
        original_dfa=observed_plant,
        original_layout=base.layout,
    )


def build_observer_dfa(plant: DFA, observable: frozenset[str]) -> DFA:
    observer_events = plant.events & observable
    initial_belief = unobservable_closure(plant, {plant.initial}, observable)
    initial_name = _belief_name(initial_belief)

    states: set[State] = {initial_name}
    transitions: dict[tuple[State, str], State] = {}
    queue: deque[frozenset[State]] = deque([initial_belief])
    visited: set[frozenset[State]] = set()

    while queue:
        belief = queue.popleft()

        if belief in visited:
            continue

        visited.add(belief)
        source_name = _belief_name(belief)

        for successor in observable_successors(plant, belief, observable):
            target_name = _belief_name(successor.closed_belief)
            states.add(target_name)
            transitions[(source_name, successor.event)] = target_name

            if successor.closed_belief not in visited and successor.closed_belief not in queue:
                queue.append(successor.closed_belief)

    return DFA(
        states=frozenset(states),
        initial=initial_name,
        events=frozenset(observer_events),
        controllable=plant.controllable & observer_events,
        observable=frozenset(observer_events),
        transitions=transitions,
    )


def _belief_name(belief: frozenset[State]) -> State:
    return "{" + ",".join(sorted(belief)) + "}"


def tagged_belief_name(belief: frozenset[State], tag: ObservationTag) -> State:
    return f"{_belief_name(belief)}:{tag.value}"


def _observer_layout(observer: DFA) -> dict[State, tuple[float, float]]:
    states = sorted(observer.states)

    if not states:
        return {}

    columns = 3
    spacing_x = 3.4
    spacing_y = 2.0

    return {
        state: ((index % columns) * spacing_x, -(index // columns) * spacing_y)
        for index, state in enumerate(states)
    }
