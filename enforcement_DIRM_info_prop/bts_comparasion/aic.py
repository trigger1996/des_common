"""Single-estimate Y/Z BTS baselines for Example 5.

The state types and edges follow Yin--Lafortune, Sections IV--VI:
Y = Q subset X, Z = (Q, gamma), Y -> Z by UR_gamma, and Z -> Y by NX.
High uses the original DFA with fixed observable events h and o. Low uses
DIRM low UR on the augmented DFA. Its NX combines ordinary and release
successors under the event label, so the graph deliberately forgets the
release distinction and is not an exact DIRM observer.

For opacity, terminal states are permitted as in Remark V.2 of the uniform
paper, which relaxes deadlock freedom for properties independent of liveness.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, FrozenSet, Iterable, Mapping, Tuple, Union

from dirm.augmented import AugmentedDFA, AugmentedState
from dirm.dfa import DFA, State
from dirm.paper_example import example_5_plant


Estimate = FrozenSet[State | AugmentedState]
Pattern = FrozenSet[str]


@dataclass(frozen=True)
class YState:
    estimate: Estimate


@dataclass(frozen=True)
class ZState:
    estimate: Estimate
    gamma: Pattern


Node = Union[YState, ZState]


@dataclass(frozen=True)
class BEdge:
    target: Node
    label: str


@dataclass(frozen=True)
class ComparisonResult:
    initial_winning: bool
    winning: FrozenSet[Node]
    policy: Mapping[YState, FrozenSet[Pattern]]
    supervisor: Mapping[YState, Pattern]


class AICBTS:
    """Construct a Y/Z BTS and prune it into its opacity AES."""

    def __init__(
        self, plant: DFA, *, mode: str, system: AugmentedDFA | None = None,
        controllable: Iterable[str], uncontrollable: Iterable[str],
    ) -> None:
        if mode not in {"high", "low"}:
            raise ValueError("mode must be 'high' or 'low'")
        self.plant = plant
        self.mode = mode
        self.system = system
        if mode == "low" and system is None:
            raise ValueError("low BTS requires the DIRM augmented system")
        self.observable = frozenset({"h", "o"} if mode == "high" else {"o"})
        self.unobservable = plant.alphabet - self.observable
        self.controllable = frozenset(controllable)
        self.uncontrollable = frozenset(uncontrollable)
        if self.controllable | self.uncontrollable != plant.alphabet:
            raise ValueError("control events must cover the plant alphabet")
        if self.controllable & self.uncontrollable:
            raise ValueError("control event sets must be disjoint")
        initial = plant.initial if mode == "high" else system.initial
        self.initial = YState(frozenset({initial}))
        self.graph: Dict[Node, Tuple[BEdge, ...]] = {}
        self.reduction_stats = {"control_edges": 0, "states": 0}

    def control_patterns(self) -> Tuple[Pattern, ...]:
        events = sorted(self.controllable)
        return tuple(
            frozenset(self.uncontrollable | frozenset(choice))
            for count in range(len(events) + 1)
            for choice in combinations(events, count)
        )

    def _static_ur(self, seeds: Estimate, gamma: Pattern) -> Estimate:
        """Uniform paper Eq. (3): UR under fixed hidden Sigma_uo."""
        reached = set(seeds)
        todo = deque(seeds)
        while todo:
            source = todo.popleft()
            for event in gamma & self.unobservable:
                target = (
                    self.plant.step(source, event)
                    if self.mode == "high" else self.system.step(source, event)
                )
                if target is not None and target not in reached:
                    reached.add(target)
                    todo.append(target)
        return frozenset(reached)

    def post_control(self, y: YState, gamma: Pattern) -> ZState:
        estimate = (
            self._static_ur(y.estimate, gamma)
            if self.mode == "high"
            else self.system.ur_tilde_low(y.estimate, enabled=gamma)
        )
        return ZState(estimate, gamma)

    def post_observation(self, z: ZState) -> FrozenSet[BEdge]:
        edges = set()
        if self.mode == "high":
            for event in z.gamma & self.observable:
                estimate = frozenset(
                    target for source in z.estimate
                    if (target := self.plant.step(source, event)) is not None
                )
                if estimate:
                    edges.add(BEdge(YState(estimate), event))
        else:
            for event in z.gamma & (self.system.observable | self.system.releasable):
                estimate = self.system.nx_tilde_sigma_r(z.estimate, event)
                if event in self.system.observable:
                    estimate |= self.system.nx_tilde_sigma(z.estimate, event)
                if estimate:
                    edges.add(BEdge(YState(estimate), event))
        return frozenset(edges)

    def _reduce_equivalent_controls(self, graph: Dict[Node, set[BEdge]]) -> None:
        """Merge subset controls only if their complete NX successors agree."""
        removed = 0
        for y in tuple(graph):
            if not isinstance(y, YState):
                continue
            choices = tuple(graph[y])
            for small in choices:
                for large in choices:
                    z_small, z_large = small.target, large.target
                    if (
                        z_small.gamma < z_large.gamma
                        and z_small.estimate == z_large.estimate
                        and graph[z_small] == graph[z_large]
                    ):
                        if small in graph[y]:
                            graph[y].remove(small)
                            removed += 1
                        break
        reached = {self.initial}
        todo = deque((self.initial,))
        while todo:
            node = todo.popleft()
            for edge in graph[node]:
                if edge.target not in reached:
                    reached.add(edge.target)
                    todo.append(edge.target)
        self.reduction_stats = {
            "control_edges": removed, "states": len(graph) - len(reached)
        }
        for node in tuple(graph):
            if node not in reached:
                del graph[node]

    def construct(self, *, max_states: int = 10000) -> Mapping[Node, Tuple[BEdge, ...]]:
        graph: Dict[Node, set[BEdge]] = {self.initial: set()}
        todo = deque((self.initial,))
        seen = set()
        while todo:
            y = todo.popleft()
            if y in seen:
                continue
            seen.add(y)
            for gamma in self.control_patterns():
                z = self.post_control(y, gamma)
                label = "{" + ",".join(sorted(gamma)) + "}"
                graph.setdefault(y, set()).add(BEdge(z, label))
                graph.setdefault(z, set())
                for edge in self.post_observation(z):
                    graph[z].add(edge)
                    if edge.target not in graph:
                        graph[edge.target] = set()
                        todo.append(edge.target)
            if len(graph) > max_states:
                raise RuntimeError("AIC/BTS state limit exceeded")
        self._reduce_equivalent_controls(graph)
        self.graph = {
            node: tuple(sorted(edges, key=lambda e: (e.label, repr(e.target))))
            for node, edges in graph.items()
        }
        return self.graph

    def is_revealing(self, z: ZState) -> bool:
        original = {
            state if self.mode == "high" else state[0]
            for state in z.estimate
        }
        return bool(original) and original <= self.plant.secret_states

    def synthesize(self) -> ComparisonResult:
        """Find largest complete opacity-safe BTS and one MAX-SYNT policy."""
        if not self.graph:
            self.construct()
        winning = {
            node for node in self.graph
            if not isinstance(node, ZState) or not self.is_revealing(node)
        }
        changed = True
        while changed:
            changed = False
            for node in tuple(winning):
                successors = self.graph[node]
                keep = (
                    any(edge.target in winning for edge in successors)
                    if isinstance(node, YState)
                    else all(edge.target in winning for edge in successors)
                )
                if not keep:
                    winning.remove(node)
                    changed = True
        policy = {
            node: frozenset(
                edge.target.gamma for edge in self.graph[node]
                if edge.target in winning
            ) for node in winning if isinstance(node, YState)
        }
        selected: Dict[YState, Pattern] = {}
        if self.initial in winning:
            todo = deque((self.initial,))
            while todo:
                y = todo.popleft()
                if y in selected:
                    continue
                choices = policy[y]
                maximal = [
                    gamma for gamma in choices
                    if not any(gamma < other for other in choices)
                ]
                gamma = sorted(maximal, key=lambda p: tuple(sorted(p)))[0]
                selected[y] = gamma
                z = self.post_control(y, gamma)
                for edge in self.graph[z]:
                    if edge.target in winning and edge.target not in selected:
                        todo.append(edge.target)
        return ComparisonResult(
            self.initial in winning, frozenset(winning), policy, selected
        )


def build_example_5_comparison(mode: str) -> AICBTS:
    plant = example_5_plant()
    system = (
        AugmentedDFA(
            plant, observable={"o"}, unobservable={"a", "u"},
            releasable={"h"}, release_states={1, 4, 8},
        ) if mode == "low" else None
    )
    if system is not None:
        # Example 5 has no anonymous release caused by an event in Sigma_uo.
        # Such an edge would need an additional observation label here.
        if any(
            (target := system.step(state, event)) is not None
            and system.is_true_release(target)
            for state in system.states for event in system.unobservable
        ):
            raise ValueError("Example 5 low BTS requires no anonymous release")
    bts = AICBTS(
        plant, mode=mode, system=system,
        controllable={"a"}, uncontrollable={"h", "o", "u"},
    )
    bts.construct()
    return bts
