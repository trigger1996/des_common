from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Mapping
import networkx as nx


Event = str
State = str


@dataclass(frozen=True)
class DFA:
    """A deterministic finite automaton for a DES plant or observer."""

    states: frozenset[State]
    initial: State
    events: frozenset[Event]
    controllable: frozenset[Event]
    observable: frozenset[Event]
    transitions: Mapping[tuple[State, Event], State]

    def __post_init__(self) -> None:
        # Transition indexes and synthesis caches require an immutable plant.
        # Copy first so mutation of the caller's original dict is harmless.
        object.__setattr__(self, "transitions", MappingProxyType(dict(self.transitions)))

    @cached_property
    def uncontrollable(self) -> frozenset[Event]:
        return self.events - self.controllable

    @cached_property
    def unobservable(self) -> frozenset[Event]:
        return self.events - self.observable

    @cached_property
    def _enabled_by_state(self) -> dict[State, tuple[tuple[Event, State], ...]]:
        """Index outgoing transitions once; DFA is immutable during synthesis."""

        outgoing: dict[State, list[tuple[Event, State]]] = {state: [] for state in self.states}

        for (source, event), target in self.transitions.items():
            outgoing.setdefault(source, []).append((event, target))

        return {
            state: tuple(sorted(items, key=lambda item: item[0]))
            for state, items in outgoing.items()
        }

    def enabled(self, state: State) -> tuple[tuple[Event, State], ...]:
        return self._enabled_by_state.get(state, ())

    def enabled_targets(self, state: State) -> list[tuple[Event, State]]:
        return list(self.enabled(state))

    def to_networkx(self) -> nx.DiGraph:
        graph = nx.DiGraph()

        for state in sorted(self.states):
            graph.add_node(state)

        for (source, event), target in self.transitions.items():
            graph.add_edge(
                source,
                target,
                event=event,
                controllable=event in self.controllable,
                observable=event in self.observable,
            )

        return graph


@dataclass(frozen=True)
class DESExample:
    name: str
    dfa: DFA
    layout: dict[State, tuple[float, float]]
    description: str
    lookahead_limit: int = 3
    source_name: str | None = None
    original_dfa: DFA | None = None
    original_layout: dict[State, tuple[float, float]] | None = None
