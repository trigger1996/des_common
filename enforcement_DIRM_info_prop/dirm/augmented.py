"""Augmented DFA and the UR/NX operators used by the DIRM-observer."""

from __future__ import annotations

from collections import deque
from typing import FrozenSet, Iterable, Optional, Set, Tuple

from .dfa import DFA, DFAError, State

AugmentedState = Tuple[State, bool]


class AugmentedDFA:
    """The paper's binary augmentation of a DFA under a DIRM.

    The Boolean component is true exactly when at least one releasable event has
    occurred since the previous release.  Hence only ``(x, True)`` for
    ``x in release_states`` is a *true* information-release state.

    Augmentation itself only lifts the plant transition function to the binary
    state space.  The ``UR_tilde``/``NX_tilde`` operators below consume the
    already-built augmented system; they do not create its states or
    transitions.
    """

    def __init__(
        self,
        plant: DFA,
        *,
        observable: Iterable[str],
        unobservable: Iterable[str],
        releasable: Iterable[str],
        release_states: Iterable[State],
    ) -> None:
        self.plant = plant
        self.observable = frozenset(observable)
        self.unobservable = frozenset(unobservable)
        self.releasable = frozenset(releasable)
        self.release_states = frozenset(release_states)
        self._validate()
        self.product_states = frozenset(
            (state, pending) for state in plant.states for pending in (False, True)
        )
        self.true_release_states = frozenset((state, True) for state in self.release_states)
        self.states = self._reachable_states()

    def _validate(self) -> None:
        groups = (self.observable, self.unobservable, self.releasable)
        if set().union(*groups) != set(self.plant.alphabet):
            raise DFAError("observable, unobservable, and releasable must cover the alphabet")
        if any(first & second for index, first in enumerate(groups) for second in groups[index + 1 :]):
            raise DFAError("observable, unobservable, and releasable must be disjoint")
        if not self.release_states <= self.plant.states:
            raise DFAError("release_states must be a subset of plant.states")

    @property
    def initial(self) -> AugmentedState:
        return self.plant.initial, False

    def is_true_release(self, state: AugmentedState) -> bool:
        return state in self.true_release_states

    def step(self, state: AugmentedState, event: str) -> Optional[AugmentedState]:
        """Lift one plant transition and update only the pending-release bit.

        In particular, ``event`` is neither filtered by an observation operator
        nor by a supervisory control pattern here.
        """
        source, pending = state
        target = self.plant.step(source, event)
        if target is None:
            return None
        # A release takes effect at the current augmented state; its successor
        # starts a fresh releasable-information interval.
        if self.is_true_release(state):
            pending = False
        return target, pending or event in self.releasable

    def _reachable_states(self) -> FrozenSet[AugmentedState]:
        """Return the augmented state space reachable from ``(x0, N)`` by BFS."""
        reached = {self.initial}
        queue = deque(reached)
        while queue:
            source = queue.popleft()
            for event in sorted(self.plant.alphabet):
                target = self.step(source, event)
                if target is not None and target not in reached:
                    reached.add(target)
                    queue.append(target)
        return frozenset(reached)

    def observable_events(self, state: AugmentedState) -> FrozenSet[str]:
        """Return the paper's state-dependent high-level set ``O(x_tilde)``.

        Besides ``Sigma_o`` and ``Sigma_r``, any transition entering a true
        release state is observable, even when its event belongs to
        ``Sigma_uo``.
        """
        result = set()
        for event in self.plant.alphabet:
            target = self.step(state, event)
            if target is not None and (
                event in self.observable
                or event in self.releasable
                or self.is_true_release(target)
            ):
                result.add(event)
        return frozenset(result)

    def low_level_observable_events(self, state: AugmentedState) -> FrozenSet[str]:
        """Return the paper's state-dependent low-level set ``O_L(x_tilde)``."""
        result = set()
        for event in self.plant.alphabet:
            target = self.step(state, event)
            if target is not None and (
                event in self.observable or self.is_true_release(target)
            ):
                result.add(event)
        return frozenset(result)

    def _unobservable_reach(
        self,
        seeds: Iterable[AugmentedState],
        *,
        low_level: bool,
        enabled: Optional[Iterable[str]] = None,
    ) -> FrozenSet[AugmentedState]:
        """Inductively compute ``UR_tilde`` with respect to ``O`` or ``O_L``."""
        # Induction base in the paper: q is a subset of UR_tilde(q).  Seeds
        # are therefore inserted unconditionally; observability and control
        # constrain only successor transitions, never membership of q itself.
        result = set(seeds)
        queue = deque(result)
        candidates = self.plant.alphabet if enabled is None else frozenset(enabled)
        while queue:
            source = queue.popleft()
            observed = (
                self.low_level_observable_events(source)
                if low_level
                else self.observable_events(source)
            )
            for event in candidates:
                if event in observed:
                    continue
                target = self.step(source, event)
                if target is not None and target not in result:
                    result.add(target)
                    queue.append(target)
        return frozenset(result)

    def ur_tilde(
        self,
        states: Iterable[AugmentedState],
        *,
        enabled: Optional[Iterable[str]] = None,
    ) -> FrozenSet[AugmentedState]:
        """Paper operator ``UR_tilde(q)`` w.r.t. state-dependent ``O(x_tilde)``.

        ``enabled`` restricts the augmented transition relation and is used by
        supervisory control.  With ``enabled=None`` this is exactly the
        uncontrolled operator defined in the DIRM paper.
        """
        return self._unobservable_reach(states, low_level=False, enabled=enabled)

    def ur_tilde_low(
        self,
        states: Iterable[AugmentedState],
        *,
        enabled: Optional[Iterable[str]] = None,
    ) -> FrozenSet[AugmentedState]:
        """Paper operator ``UR_tilde_L(q)`` w.r.t. ``O_L(x_tilde)``."""
        return self._unobservable_reach(states, low_level=True, enabled=enabled)

    # Compatibility aliases for callers written before the paper notation was
    # made explicit in this package.
    def ur(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.ur_tilde(states)

    def ur_low(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.ur_tilde_low(states)

    def _next_reach(
        self, states: Iterable[AugmentedState], events: Iterable[str], *, release: bool
    ) -> FrozenSet[AugmentedState]:
        result: Set[AugmentedState] = set()
        for source in states:
            for event in events:
                target = self.step(source, event)
                if target is not None and self.is_true_release(target) == release:
                    result.add(target)
        return frozenset(result)

    def nx_tilde_sigma(
        self, states: Iterable[AugmentedState], event: str
    ) -> FrozenSet[AugmentedState]:
        """Paper operator ``NX_tilde_sigma(q)`` for ``sigma in Sigma_o U Sigma_r``.

        Successors in ``X_tilde_r`` are deliberately excluded; those belong
        to ``NX_tilde_sigma_r`` instead.
        """
        if event not in self.observable | self.releasable:
            return frozenset()
        return self._next_reach(states, (event,), release=False)

    def nx_tilde_r(
        self,
        states: Iterable[AugmentedState],
        *,
        enabled: Optional[Iterable[str]] = None,
    ) -> FrozenSet[AugmentedState]:
        """Paper operator ``NX_tilde_r(q)`` for anonymous release by ``Sigma_uo``."""
        events = self.unobservable
        if enabled is not None:
            events &= frozenset(enabled)
        return self._next_reach(states, events, release=True)

    def nx_tilde_sigma_r(
        self, states: Iterable[AugmentedState], event: str
    ) -> FrozenSet[AugmentedState]:
        """Paper operator ``NX_tilde_{sigma,r}(q)`` for visible event + release."""
        if event not in self.observable | self.releasable:
            return frozenset()
        return self._next_reach(states, (event,), release=True)

    # Compatibility aliases for the earlier short API.
    def nx(self, states: Iterable[AugmentedState], event: str) -> FrozenSet[AugmentedState]:
        return self.nx_tilde_sigma(states, event)

    def nx_release(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.nx_tilde_r(states)

    def nx_event_release(
        self, states: Iterable[AugmentedState], event: str
    ) -> FrozenSet[AugmentedState]:
        return self.nx_tilde_sigma_r(states, event)
