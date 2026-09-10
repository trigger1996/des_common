from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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
    transitions: dict[tuple[State, Event], State]

    @property
    def uncontrollable(self) -> frozenset[Event]:
        return self.events - self.controllable

    @property
    def unobservable(self) -> frozenset[Event]:
        return self.events - self.observable

    def enabled(self, state: State) -> Iterable[tuple[Event, State]]:
        for event in sorted(self.events):
            target = self.transitions.get((state, event))
            if target is not None:
                yield event, target

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
