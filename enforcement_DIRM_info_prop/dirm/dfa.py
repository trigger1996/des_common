"""Small, dependency-free deterministic finite automata primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Hashable, Iterable, Mapping, Optional, Tuple

State = Hashable
Transition = Tuple[State, str]


class DFAError(ValueError):
    """Raised when a DFA or an event partition is not well formed."""


@dataclass(frozen=True)
class DFA:
    """A partial deterministic finite automaton ``(X, Sigma, delta, x0)``.

    ``transitions`` maps ``(source, event)`` to a single successor.  A partial
    transition function is intentional: undefined transitions are not in the
    generated language.
    """

    states: FrozenSet[State]
    alphabet: FrozenSet[str]
    initial: State
    transitions: Mapping[Transition, State]
    secret_states: FrozenSet[State] = frozenset()

    def __post_init__(self) -> None:
        if self.initial not in self.states:
            raise DFAError("the initial state must belong to states")
        if not self.secret_states <= self.states:
            raise DFAError("secret_states must be a subset of states")
        for (source, event), target in self.transitions.items():
            if source not in self.states or target not in self.states:
                raise DFAError("every transition endpoint must belong to states")
            if event not in self.alphabet:
                raise DFAError("every transition event must belong to alphabet")

    @classmethod
    def build(
        cls,
        *,
        states: Iterable[State],
        alphabet: Iterable[str],
        initial: State,
        transitions: Mapping[Transition, State],
        secret_states: Iterable[State] = (),
    ) -> "DFA":
        return cls(
            frozenset(states), frozenset(alphabet), initial, dict(transitions), frozenset(secret_states)
        )

    def step(self, state: State, event: str) -> Optional[State]:
        return self.transitions.get((state, event))

    def enabled(self, state: State) -> Tuple[str, ...]:
        return tuple(event for event in self.alphabet if (state, event) in self.transitions)
