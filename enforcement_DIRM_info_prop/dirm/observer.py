"""DIRM-observer for a general DFA.

This is the finite construction in Hou, Yin and Li, *Automatica* 140 (2022),
Secs. 4--5.  It has no timing, control, plotting, YAML, or experiment code.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

from .augmented import AugmentedDFA, AugmentedState
from .dfa import DFA, State
from .verification import OpacityResult


@dataclass(frozen=True)
class ObserverState:
    """Paper state ``(x_tilde, q_hat, q)`` of the DIRM-observer."""

    x_tilde: AugmentedState
    q_hat: FrozenSet[AugmentedState]
    q: FrozenSet[AugmentedState]


class DIRMObserver:
    """Build and check the DIRM-observer of a DFA.

    ``observable``, ``unobservable``, and ``releasable`` must partition the plant
    alphabet.  ``release_states`` is ``X_r``.  For the paper's standing
    assumption, a releasable event may not enter a release state directly.
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
        self.system = AugmentedDFA(
            plant,
            observable=observable,
            unobservable=unobservable,
            releasable=releasable,
            release_states=release_states,
        )
        self.plant = self.system.plant

    # These delegates retain the paper's tilde-operator notation at the API.
    def ur_tilde(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.system.ur_tilde(states)

    def ur_tilde_low(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.system.ur_tilde_low(states)

    # Backward-compatible short names.
    def ur(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.ur_tilde(states)

    def ur_low(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.ur_tilde_low(states)

    def nx_tilde_sigma(
        self, states: Iterable[AugmentedState], event: str
    ) -> FrozenSet[AugmentedState]:
        return self.system.nx_tilde_sigma(states, event)

    def nx_tilde_r(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.system.nx_tilde_r(states)

    def nx_tilde_sigma_r(
        self, states: Iterable[AugmentedState], event: str
    ) -> FrozenSet[AugmentedState]:
        return self.system.nx_tilde_sigma_r(states, event)

    # Backward-compatible short names.
    def nx(self, states: Iterable[AugmentedState], event: str) -> FrozenSet[AugmentedState]:
        return self.nx_tilde_sigma(states, event)

    def nx_release(self, states: Iterable[AugmentedState]) -> FrozenSet[AugmentedState]:
        return self.nx_tilde_r(states)

    def nx_event_release(
        self, states: Iterable[AugmentedState], event: str
    ) -> FrozenSet[AugmentedState]:
        return self.nx_tilde_sigma_r(states, event)

    def successor(self, state: ObserverState, event: str) -> Optional[ObserverState]:
        """Apply Eqs. (4)--(5) of the DIRM-observer definition.

        ``q_mid`` is the paper's intermediate estimate.  On a true release, it is
        deliberately reused for the low-level estimate: the released history
        makes the high-level information available to the intruder.
        """
        x_tilde_prime = self.system.step(state.x_tilde, event)
        if x_tilde_prime is None:
            return None
        released = self.system.is_true_release(x_tilde_prime)
        high_visible = event in self.system.observable or event in self.system.releasable or released
        low_visible = event in self.system.observable or released

        if not high_visible:
            q_hat_prime = state.q_hat
        else:
            if released and event in self.system.unobservable:
                q_mid = self.nx_tilde_r(state.q_hat)
            elif released:
                q_mid = self.nx_tilde_sigma_r(state.q_hat, event)
            else:
                q_mid = self.nx_tilde_sigma(state.q_hat, event)
            q_hat_prime = self.ur_tilde(q_mid)

        if not low_visible:
            q_prime = state.q
        elif released:
            # Eq. (4): a release switches the low-level estimate to q_mid.
            q_prime = self.ur_tilde_low(q_mid)
        else:
            q_prime = self.ur_tilde_low(self.nx_tilde_sigma(state.q, event))
        return ObserverState(x_tilde_prime, q_hat_prime, q_prime)

    def initial_state(self) -> ObserverState:
        start = self.system.initial
        return ObserverState(start, self.ur_tilde({start}), self.ur_tilde_low({start}))

    def reachable(self) -> Tuple[Mapping[ObserverState, Mapping[str, ObserverState]], Mapping[ObserverState, Tuple[str, ...]]]:
        """Return reachable observer graph and a shortest plant-word for each state."""
        initial = self.initial_state()
        graph: Dict[ObserverState, Dict[str, ObserverState]] = {initial: {}}
        words: Dict[ObserverState, Tuple[str, ...]] = {initial: ()}
        todo = deque([initial])
        while todo:
            current = todo.popleft()
            for event in sorted(self.plant.alphabet):
                target = self.successor(current, event)
                if target is None:
                    continue
                graph[current][event] = target
                if target not in graph:
                    graph[target] = {}
                    words[target] = words[current] + (event,)
                    todo.append(target)
        return graph, words

    def check_current_state_opacity(self) -> OpacityResult:
        """Compatibility convenience method; see ``verification`` for Theorem 2."""
        from .verification import verify_current_state_opacity

        return verify_current_state_opacity(self)
