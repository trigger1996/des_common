from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from des_core.automata import DFA, Event, State
from des_core.ll_bts import construct_ll_bts


ProductState = tuple[State, ...]


@dataclass(frozen=True)
class ImplicitProductDFA:
    component: DFA
    copies: int

    @property
    def initial(self) -> ProductState:
        return tuple(self.component.initial for _index in range(self.copies))

    @property
    def state_count(self) -> int:
        return len(self.component.states) ** self.copies

    @property
    def events(self) -> frozenset[Event]:
        return frozenset(
            _product_event(index, event)
            for index in range(self.copies)
            for event in self.component.events
        )

    @property
    def controllable(self) -> frozenset[Event]:
        return frozenset()

    @property
    def uncontrollable(self) -> frozenset[Event]:
        return self.events

    @property
    def observable(self) -> frozenset[Event]:
        return self.events

    @property
    def unobservable(self) -> frozenset[Event]:
        return frozenset()

    def enabled(self, state: ProductState) -> tuple[tuple[Event, ProductState], ...]:
        successors: list[tuple[Event, ProductState]] = []
        # Asynchronous interleaving product: a transition updates exactly one
        # component and labels the event with that component index. This is not
        # a synchronous tuple-event product such as (a, u, b, ...).
        for index, component_state in enumerate(state):
            for event, target in self.component.enabled(component_state):
                next_state = list(state)
                next_state[index] = target
                successors.append((_product_event(index, event), tuple(next_state)))
        return tuple(successors)

    def enabled_targets(self, state: ProductState) -> list[tuple[Event, ProductState]]:
        return list(self.enabled(state))


@dataclass(frozen=True)
class ProductIterationStats:
    iteration: int
    current: ProductState
    local_state_count: int
    decision_estimate_state_count: int
    observation_estimate_state_count: int
    decision_information_state_count: int
    observation_information_state_count: int
    new_state_count: int
    cumulative_state_count: int
    local_edge_count: int
    selected_event: Event | None
    next_state: ProductState | None


@dataclass(frozen=True)
class ProductBenchmarkResult:
    copies: int
    global_state_count: int
    iterations: int
    horizon: int
    elapsed_seconds: float
    max_local_states: int
    max_local_edges: int
    stats: tuple[ProductIterationStats, ...]


def benchmark_case1_product(
    component: DFA,
    copies: int,
    iterations: int,
    horizon: int,
    progress: Callable[[ProductIterationStats, int, float], None] | None = None,
) -> ProductBenchmarkResult:
    product = ImplicitProductDFA(component=component, copies=copies)
    current = product.initial
    cumulative_states: set[ProductState] = set()
    stats: list[ProductIterationStats] = []
    start = perf_counter()

    for iteration in range(iterations):
        ll_bts = construct_ll_bts(product, current, horizon, store_edges=False)
        local_states = ll_bts.searched_states
        previous_cumulative = len(cumulative_states)
        cumulative_states.update(local_states)
        new_state_count = len(cumulative_states) - previous_cumulative
        enabled = product.enabled(current)
        selected_event, next_state = enabled[iteration % len(enabled)] if enabled else (None, None)
        stats.append(
            ProductIterationStats(
                iteration=iteration,
                current=current,
                local_state_count=len(local_states),
                decision_estimate_state_count=len(ll_bts.decision_estimate_states),
                observation_estimate_state_count=len(ll_bts.observation_estimate_states),
                decision_information_state_count=len(ll_bts.decision_states),
                observation_information_state_count=len(ll_bts.observation_states),
                new_state_count=new_state_count,
                cumulative_state_count=len(cumulative_states),
                local_edge_count=ll_bts.edge_count,
                selected_event=selected_event,
                next_state=next_state,
            )
        )
        if progress is not None:
            progress(stats[-1], iterations, perf_counter() - start)
        if next_state is None:
            break
        current = next_state

    elapsed = perf_counter() - start
    return ProductBenchmarkResult(
        copies=copies,
        global_state_count=product.state_count,
        iterations=len(stats),
        horizon=horizon,
        elapsed_seconds=elapsed,
        max_local_states=max((item.local_state_count for item in stats), default=0),
        max_local_edges=max((item.local_edge_count for item in stats), default=0),
        stats=tuple(stats),
    )


def post_leq_product(
    product: ImplicitProductDFA,
    seeds: set[ProductState],
    horizon: int,
) -> tuple[frozenset[ProductState], frozenset[tuple[ProductState, Event, ProductState]]]:
    reached: set[ProductState] = set(seeds)
    edges: set[tuple[ProductState, Event, ProductState]] = set()
    queue: deque[tuple[ProductState, int]] = deque((state, 0) for state in seeds)
    while queue:
        state, depth = queue.popleft()
        if depth >= horizon:
            continue
        for event, target in product.enabled(state):
            edges.add((state, event, target))
            if target in reached:
                continue
            reached.add(target)
            queue.append((target, depth + 1))
    return frozenset(reached), frozenset(edges)


def product_state_label(state: ProductState) -> str:
    return "(" + ",".join(state) + ")"


def _product_event(index: int, event: Event) -> Event:
    return f"{event}_{index}"
