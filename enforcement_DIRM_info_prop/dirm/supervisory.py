"""Observation-based tripartite supervisory control for a DIRM plant.

The information-state spaces are

``I <= 2^X x 2^X``, ``J <= 2^X x 2^X x Gamma``, and
``L <= 2^X x Gamma``.

They implement the paper's control, observation, and release states,
respectively.

Here ``X`` is the DIRM augmented plant state space.  The two set-valued
components are the paper's high-level estimate ``q_hat`` and DIRM estimate
``q``; no I- or J-state contains an exact plant state.  At the set-valued
information-state level, a J-state returns directly to I after an ordinary
observation, or reaches I through ``J -> L -> I`` after a release.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple, Union

from .augmented import AugmentedState
from .dfa import DFA, DFAError, State
from .observer import DIRMObserver
from .release_language import (
    EMPTY, EPSILON, Language, recursive_transition_labels, symbol, union,
)


ControlPattern = FrozenSet[str]
Estimate = FrozenSet[AugmentedState]


@dataclass(frozen=True)
class IState:
    """Code-level I-state for a paper control state ``(q_hat, q)``."""

    q_hat: Estimate
    q: Estimate


@dataclass(frozen=True)
class JState:
    """Code-level J-state for an observation state ``(q_hat, q, gamma)``."""

    q_hat: Estimate
    q: Estimate
    gamma: ControlPattern


@dataclass(frozen=True)
class LState:
    """Code-level L-state for a release state ``(q_mid, gamma)``."""

    q_mid: Estimate
    gamma: ControlPattern


BTSState = Union[IState, JState, LState]


@dataclass(frozen=True)
class BTSEdge:
    target: BTSState
    kind: str
    gamma: Optional[ControlPattern] = None
    sigma: Optional[str] = None
    release_language: Optional[Language] = None


@dataclass(frozen=True)
class SynthesisResult:
    initial_winning: bool
    winning_states: FrozenSet[BTSState]
    policy: Mapping[IState, FrozenSet[ControlPattern]]
    secret_revealing_states: FrozenSet[BTSState] = frozenset()
    secret_only_states: FrozenSet[BTSState] = frozenset()
    inconsistent_states: FrozenSet[BTSState] = frozenset()
    removal_rounds: Mapping[BTSState, int] = field(default_factory=dict)
    removal_reasons: Mapping[BTSState, str] = field(default_factory=dict)
    blocked_successors: Mapping[BTSState, FrozenSet[BTSState]] = field(default_factory=dict)


class SupervisoryDIRMBTS:
    """Build and solve the observation-based I-J-L DIRM safety game."""

    def __init__(
        self,
        plant: DFA,
        *,
        controllable: Iterable[str],
        uncontrollable: Iterable[str],
        observable: Iterable[str],
        unobservable: Iterable[str],
        releasable: Iterable[str],
        release_states: Iterable[State],
    ) -> None:
        self.observer = DIRMObserver(
            plant,
            observable=observable,
            unobservable=unobservable,
            releasable=releasable,
            release_states=release_states,
        )
        self.system = self.observer.system
        self.plant = plant
        self.controllable = frozenset(controllable)
        self.uncontrollable = frozenset(uncontrollable)
        if self.controllable | self.uncontrollable != plant.alphabet:
            raise DFAError("controllable and uncontrollable must cover the alphabet")
        if self.controllable & self.uncontrollable:
            raise DFAError("controllable and uncontrollable must be disjoint")

        start = frozenset({self.system.initial})
        self.initial = IState(start, start)
        self.graph: Dict[BTSState, Tuple[BTSEdge, ...]] = {}
        self.reduction_stats = {"control_edges": 0, "states": 0}

    @property
    def structure(self) -> str:
        return "I-J-(I|L)-I"

    def control_patterns(self) -> Tuple[ControlPattern, ...]:
        events = sorted(self.controllable)
        return tuple(
            frozenset(self.uncontrollable | frozenset(choice))
            for size in range(len(events) + 1)
            for choice in combinations(events, size)
        )

    def _ur_tilde(self, states: Iterable[AugmentedState], gamma: ControlPattern) -> Estimate:
        return self.system.ur_tilde(states, enabled=gamma)

    def _ur_tilde_low(
        self, states: Iterable[AugmentedState], gamma: ControlPattern
    ) -> Estimate:
        return self.system.ur_tilde_low(states, enabled=gamma)

    def _nx_tilde_sigma(self, states: Iterable[AugmentedState], sigma: str) -> Estimate:
        return self.system.nx_tilde_sigma(states, sigma)

    def post_control(self, state: IState, gamma: ControlPattern) -> JState:
        """Apply ``gamma`` and return one ``(q_hat, q, gamma)`` J-state."""
        return JState(
            self._ur_tilde(state.q_hat, gamma),
            self._ur_tilde_low(state.q, gamma),
            gamma,
        )

    def _observable_successor(self, state: JState, sigma: str) -> Optional[IState]:
        """Apply a non-release instant observation ``sigma in Sigma_o``."""
        q_hat_mid = self._nx_tilde_sigma(state.q_hat, sigma)
        q_mid = self._nx_tilde_sigma(state.q, sigma)
        if not q_hat_mid or not q_mid:
            return None
        return IState(q_hat_mid, q_mid)

    def _release_prefix_step(self, state: JState, sigma: str) -> Optional[JState]:
        """Follow one unreleased ``Sigma_r`` label inside the fixed ``x_L`` graph.

        This is the single graph operation represented in the paper by a
        release-prefix path.  It combines the former ``NX`` then ``UR`` pair:
        first take non-release ``sigma`` transitions, then close under enabled
        ``Sigma_uo`` transitions that still do not release information.  The
        low-level estimate is the fixed vertex set of this local search.
        """
        if sigma not in state.gamma or sigma not in self.system.releasable:
            return None

        reached = set()
        for source in state.q_hat:
            target = self.system.step(source, sigma)
            if (
                target is not None
                and not self.system.is_true_release(target)
                and target in state.q
            ):
                reached.add(target)
        if not reached:
            return None

        todo = deque(reached)
        hidden = state.gamma & self.system.unobservable
        while todo:
            source = todo.popleft()
            for event in hidden:
                target = self.system.step(source, event)
                if (
                    target is not None
                    and not self.system.is_true_release(target)
                    and target in state.q
                    and target not in reached
                ):
                    reached.add(target)
                    todo.append(target)
        return JState(frozenset(reached), state.q, state.gamma)

    def _observation_graph(
        self, seed: JState
    ) -> Dict[JState, Tuple[Tuple[str, JState], ...]]:
        """Finite local high-level graph, retaining its releasable labels."""
        graph = {}
        reached = {seed}
        todo = deque([seed])
        while todo:
            current = todo.popleft()
            outgoing = []
            for sigma in sorted(current.gamma & self.system.releasable):
                successor = self._release_prefix_step(current, sigma)
                if successor is not None:
                    outgoing.append((sigma, successor))
                    if successor not in reached:
                        reached.add(successor)
                        todo.append(successor)
            graph[current] = tuple(outgoing)
        return graph

    def _release_targets(self, state: JState) -> Dict[str, Estimate]:
        """Return every unified paper successor ``NX_tilde_sigma_r(x_hat)``.

        A visible or releasable terminal event forms a singleton observation
        class.  Every enabled ``Sigma_uo`` trigger belongs to one anonymous
        class, so its successor estimate contains all indistinguishable
        unobservable release transitions.  All per-event targets are computed
        once, and the anonymous union is then shared by its triggering events.
        """
        per_event = {}
        for sigma in state.gamma:
            targets = frozenset(
                target
                for source in state.q_hat
                if (target := self.system.step(source, sigma)) is not None
                and self.system.is_true_release(target)
            )
            if targets:
                per_event[sigma] = targets
        anonymous = frozenset().union(*(
            targets for sigma, targets in per_event.items()
            if sigma in self.system.unobservable
        ))
        return {
            sigma: anonymous if sigma in self.system.unobservable else targets
            for sigma, targets in per_event.items()
        }

    def _release_successors(self, state: JState) -> Tuple[Tuple[str, LState], ...]:
        return tuple(
            (sigma, LState(q_mid, state.gamma))
            for sigma, q_mid in sorted(self._release_targets(state).items())
        )

    def _release_update(self, state: LState) -> IState:
        """Fuse released information before the next control decision."""
        return IState(state.q_mid, state.q_mid)

    @staticmethod
    def _z_successor_signature(
        state: JState, adjacency: Mapping[BTSState, list[BTSEdge]]
    ) -> FrozenSet[tuple]:
        """Return every labeled successor, normalized only for its control label.

        Ordinary branches contain the exact successor I-state.  Release
        branches contain the released L information and its exact successor
        I-state after the mandatory update.  Thus equal estimates and a common
        predecessor alone can never trigger reduction when successors differ.
        """
        outcomes = set()
        for edge in adjacency[state]:
            if edge.kind == "JI":
                outcomes.add(("JI", edge.sigma, edge.target))
            else:
                l_state = edge.target
                update_edges = adjacency[l_state]
                if len(update_edges) != 1 or not isinstance(update_edges[0].target, IState):
                    raise RuntimeError("every L-state must have exactly one I update")
                outcomes.add(
                    (
                        "JL",
                        edge.sigma,
                        l_state.q_mid,
                        l_state.gamma,
                        update_edges[0].target,
                    )
                )
        return frozenset(outcomes)

    def _reduce_dominated_controls(
        self, adjacency: Dict[BTSState, list[BTSEdge]]
    ) -> Dict[BTSState, list[BTSEdge]]:
        """Remove locally redundant J choices and their unreachable branches.

        For one predecessor I, a control choice ``gamma_1`` is dominated by
        ``gamma_2`` when ``gamma_1`` is a proper subset of ``gamma_2``, both
        produce the same high/low J estimate, and their complete ordinary and
        release/high-level outcome signatures coincide.  Retaining the larger
        pattern is behavior preserving and more permissive.
        """
        removed_edges = 0
        for source in tuple(adjacency):
            if not isinstance(source, IState):
                continue
            choices = [edge for edge in adjacency[source] if isinstance(edge.target, JState)]
            dominated = set()
            for smaller in choices:
                z_small = smaller.target
                for larger in choices:
                    z_large = larger.target
                    if not z_small.gamma < z_large.gamma:
                        continue
                    if z_small.q_hat != z_large.q_hat or z_small.q != z_large.q:
                        continue
                    if self._z_successor_signature(
                        z_small, adjacency
                    ) != self._z_successor_signature(z_large, adjacency):
                        continue
                    dominated.add(smaller)
                    break
            if dominated:
                adjacency[source] = [
                    edge for edge in adjacency[source] if edge not in dominated
                ]
                removed_edges += len(dominated)

        reachable = {self.initial}
        todo = deque([self.initial])
        while todo:
            source = todo.popleft()
            for edge in adjacency[source]:
                if edge.target not in reachable:
                    reachable.add(edge.target)
                    todo.append(edge.target)
        removed_states = len(adjacency) - len(reachable)
        self.reduction_stats = {
            "control_edges": removed_edges,
            "states": removed_states,
        }
        return {state: adjacency[state] for state in adjacency if state in reachable}

    def construct(self, *, max_states: int = 10000) -> Mapping[BTSState, Tuple[BTSEdge, ...]]:
        """Construct the controlled decomposition of observer Eqs. (2)--(5)."""
        adjacency: Dict[BTSState, list[BTSEdge]] = {self.initial: []}

        def add_edge(source: BTSState, edge: BTSEdge) -> None:
            adjacency.setdefault(source, [])
            adjacency.setdefault(edge.target, [])
            if edge not in adjacency[source]:
                adjacency[source].append(edge)

        todo = deque([self.initial])
        expanded_i = set()
        while todo:
            i_state = todo.popleft()
            if i_state in expanded_i:
                continue
            expanded_i.add(i_state)

            for gamma in self.control_patterns():
                j_state = self.post_control(i_state, gamma)
                add_edge(i_state, BTSEdge(j_state, "IJ", gamma=gamma))

                # Solve release transitions recursively on SCC supernodes,
                # then map their labels back to the original J->L edges.
                # No internal J node is added to the TTS graph.
                local_graph = self._observation_graph(j_state)
                direct: Dict[JState, Dict[Tuple[str, LState], Language]] = {}
                for internal_j in local_graph:
                    for sigma in sorted(internal_j.gamma & self.system.observable):
                        next_i = self._observable_successor(internal_j, sigma)
                        if next_i is not None:
                            add_edge(j_state, BTSEdge(next_i, "JI", sigma=sigma))
                            if next_i not in expanded_i:
                                todo.append(next_i)

                    for sigma, l_state in self._release_successors(internal_j):
                        next_i = self._release_update(l_state)
                        label = (
                            symbol(sigma)
                            if sigma in self.system.observable | self.system.releasable
                            else EPSILON
                        )
                        key = (sigma, l_state)
                        node_direct = direct.setdefault(internal_j, {})
                        node_direct[key] = union(node_direct.get(key, EMPTY), label)
                        add_edge(l_state, BTSEdge(next_i, "LI"))
                        if next_i not in expanded_i:
                            todo.append(next_i)
                releases = recursive_transition_labels(local_graph, j_state, direct)
                for (sigma, l_state), language in releases.items():
                    add_edge(
                        j_state,
                        BTSEdge(l_state, "JL", sigma=sigma, release_language=language),
                    )

                if len(adjacency) > max_states:
                    raise RuntimeError(
                        f"{self.structure} construction exceeded max_states={max_states}"
                    )

        adjacency = self._reduce_dominated_controls(adjacency)
        self.graph = {state: tuple(edges) for state, edges in adjacency.items()}
        return self.graph

    def _estimate(self, state: BTSState) -> Estimate:
        return state.q_mid if isinstance(state, LState) else state.q

    def is_revealing(self, state: BTSState) -> bool:
        estimate = {original for original, _ in self._estimate(state)}
        return bool(estimate) and estimate <= self.plant.secret_states

    def synthesize(self) -> SynthesisResult:
        """Compute the greatest fixed point of the opacity safety game."""
        if not self.graph:
            self.construct()
        secret_only = frozenset(state for state in self.graph if self.is_revealing(state))
        revealing = frozenset(state for state in secret_only if isinstance(state, JState))
        winning = set(self.graph) - secret_only
        rounds = {state: 0 for state in secret_only}
        reasons = {state: "secret-only low-level estimate" for state in secret_only}
        blocked = {}
        inconsistent = set()
        round_number = 1
        while True:
            removed = set()
            # Evaluate each round against one retained-state set so the
            # explanation is independent of hash/set iteration order.
            for state in winning:
                edges = self.graph[state]
                if isinstance(state, IState):
                    keep = any(edge.target in winning for edge in edges)
                    reason = "(i) no control successor remains"
                elif isinstance(state, JState):
                    keep = all(edge.target in winning for edge in edges)
                    reason = "(ii) an observation/release successor was removed"
                else:
                    keep = len(edges) == 1 and edges[0].target in winning
                    reason = "(iii) the required release return is missing or removed"
                if not keep:
                    removed.add(state)
                    rounds[state] = round_number
                    reasons[state] = reason
                    blocked[state] = frozenset(
                        edge.target for edge in edges if edge.target not in winning
                    )
            if not removed:
                break
            winning.difference_update(removed)
            inconsistent.update(removed)
            round_number += 1

        policy = {}
        for state in winning:
            if isinstance(state, IState):
                policy[state] = frozenset(
                    edge.gamma
                    for edge in self.graph[state]
                    if edge.gamma is not None and edge.target in winning
                )
        return SynthesisResult(
            self.initial in winning, frozenset(winning), policy,
            revealing, secret_only, frozenset(inconsistent), rounds, reasons, blocked,
        )

    def state_counts(self) -> Mapping[str, int]:
        return {
            "I": sum(isinstance(state, IState) for state in self.graph),
            "J": sum(isinstance(state, JState) for state in self.graph),
            "L": sum(isinstance(state, LState) for state in self.graph),
        }
