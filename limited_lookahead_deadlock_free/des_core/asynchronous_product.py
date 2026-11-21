"""Implicit asynchronous (interleaving) product of arbitrary DFA components."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Set
from itertools import product as cartesian_product
from functools import cached_property, lru_cache
from math import prod

from des_core.automata import DFA, Event, State

ProductState = tuple[State, ...]


class ProductStateSpace(Set):
    """Known Cartesian state space with lazy iteration and constant-space membership."""

    def __init__(self, components):self.components = components

    def __len__(self):return prod(len(c.states) for c in self.components)

    def __iter__(self):return cartesian_product(*(sorted(c.states) for c in self.components))

    def __contains__(self, state):
        return (isinstance(state, tuple) and len(state) == len(self.components)
                and all(q in c.states for q, c in zip(state, self.components)))

    @classmethod
    def _from_iterable(cls, values):
        # Set algebra materializes its result; it must not reinterpret states as
        # component DFA objects through this view's constructor.
        return frozenset(values)


def product_event(index: int, event: Event) -> Event:
    return f"{event}_{index}"


@dataclass(frozen=True)
class AsynchronousProductDFA:
    """One local event updates one component; other coordinates stay fixed.

    Events are indexed by their owning component, even if component alphabets
    overlap. Controllability and observability inherit from that owner:
    e_i is controllable iff e is controllable in G_i, and likewise observable.
    This is interleaving, not synchronization on shared event names.
    """

    components: tuple[DFA, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", tuple(self.components))

        if not self.components:
            raise ValueError("an asynchronous product needs at least one component")

    @property
    def initial(self) -> ProductState:
        return tuple(component.initial for component in self.components)

    @property
    def state_count(self) -> int:
        return prod(len(component.states) for component in self.components)

    @cached_property
    def states(self):
        return ProductStateSpace(self.components)

    def _indexed_events(self, attribute: str) -> frozenset[Event]:
        return frozenset(
            product_event(index, event)
            for index, component in enumerate(self.components)
            for event in getattr(component, attribute)
        )

    @cached_property
    def events(self) -> frozenset[Event]:
        return self._indexed_events("events")

    @cached_property
    def controllable(self) -> frozenset[Event]:
        return self._indexed_events("controllable")

    @cached_property
    def uncontrollable(self) -> frozenset[Event]:
        return self.events - self.controllable

    @cached_property
    def observable(self) -> frozenset[Event]:
        return self._indexed_events("observable")

    @cached_property
    def unobservable(self) -> frozenset[Event]:
        return self.events - self.observable

    @cached_property
    def _cached_enabled(self):
        return lru_cache(maxsize=16384)(self._compute_enabled)

    def enabled(self, state: ProductState) -> tuple[tuple[Event, ProductState], ...]:
        if len(state) != len(self.components):
            raise ValueError("product state must have one coordinate per component")

        return self._cached_enabled(state)

    def _compute_enabled(self, state: ProductState) -> tuple[tuple[Event, ProductState], ...]:
        successors = []

        for index, component in enumerate(self.components):
            for event, target in component.enabled(state[index]):
                next_state = list(state)
                next_state[index] = target
                successors.append((product_event(index, event), tuple(next_state)))

        return tuple(successors)

    def enabled_targets(self, state: ProductState) -> list[tuple[Event, ProductState]]:
        return list(self.enabled(state))


class ImplicitProductDFA(AsynchronousProductDFA):
    """Compatibility constructor for identical copies of one component."""

    def __init__(self, component: DFA, copies: int):
        if copies < 1:
            raise ValueError("copies must be positive")

        super().__init__((component,) * copies)

    @property
    def component(self) -> DFA:
        return self.components[0]

    @property
    def copies(self) -> int:
        return len(self.components)
