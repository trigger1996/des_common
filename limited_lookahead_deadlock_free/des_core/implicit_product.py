from __future__ import annotations

from collections import deque, OrderedDict
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from des_core.automata import DFA, Event, State
from des_core.ll_bts import construct_ll_bts
from des_core.ll_bts_synthesis import solve_ll_bts


# Compatibility re-exports; all product semantics live in the generic module.
from des_core.asynchronous_product import (
    AsynchronousProductDFA, ImplicitProductDFA, ProductState,
    product_event as _product_event,
)


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
    step_seconds: float = 0.0
    cache_hit: bool = False
    construction_strategy: str = "full"
    synthesis_passes: int = 1


@dataclass(frozen=True)
class ProductCycleCheck:
    ok: bool
    path: tuple[tuple[ProductState, Event, ProductState], ...]
    message: str


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
    cycle_check: ProductCycleCheck
    stop_reason: str = "iteration_limit"
    pattern_mode: str = "factored"
    synthesis_calls: int = 0
    cache_hits: int = 0
    successor_policy: str = "round-robin"


def benchmark_case1_product(
    component: DFA,
    copies: int,
    iterations: int,
    horizon: int,
    progress: Callable[[ProductIterationStats, int, float], None] | None=None,
    require_full_iterations: bool=True,
    expansion_progress: Callable[[int, int, int], None] | None=None,
    *, pattern_mode: str="factored", cache_size: int=0,
    use_certificate: bool=True,
) -> ProductBenchmarkResult:
    if iterations < 1 or horizon < 0 or cache_size < 0:
        raise ValueError("iterations must be positive; horizon/cache_size nonnegative")

    product = ImplicitProductDFA(component=component, copies=copies)
    current = product.initial
    cumulative_states: set[ProductState] = set()
    stats: list[ProductIterationStats] = []
    cycle_check = verify_case1_product_cycle(product)
    # Retain require_full_iterations for caller compatibility. Algorithm 2
    # termination is normal even when the requested iteration limit is not met.
    stop_reason = "iteration_limit"
    start = perf_counter()
    cache = OrderedDict()
    synthesis_calls = 0
    cache_hits = 0

    for iteration in range(iterations):
        step_start = perf_counter()
        # The plant, horizon and mode are fixed for this run. An identical root
        # gives an identical window and synthesis. Cache only the compact result
        # and statistics, never the potentially large D/O graph.
        cached = cache.get(current)
        cache_hit = cached is not None

        if cache_hit:
            cache_hits += 1
            cache.move_to_end(current)
            local_states, counts, control, strategy = cached
            synthesis_passes = 0
        else:
            ll_bts, control = solve_ll_bts(
                product, current, horizon, use_certificate=use_certificate,
                expansion_progress=expansion_progress, pattern_mode=pattern_mode,
            )
            synthesis_calls += 1
            local_states = ll_bts.searched_states
            counts = (len(ll_bts.decision_estimate_states),
                      len(ll_bts.observation_estimate_states),
                      len(ll_bts.decision_states), len(ll_bts.observation_states),
                      ll_bts.edge_count)
            strategy = ll_bts.construction_strategy
            synthesis_passes = ll_bts.synthesis_passes
            del ll_bts

            if cache_size:
                cache[current] = local_states, counts, control, strategy

                if len(cache) > cache_size:
                    cache.popitem(last=False)

        previous_cumulative = len(cumulative_states)
        cumulative_states.update(local_states)
        new_state_count = len(cumulative_states) - previous_cumulative
        selected_event, next_state = None, None

        if control.empty:
            # Algorithm 2: if the pruned rooted S is empty, Return.
            stop_reason = "empty_synthesis"
        elif not control.forward_successors:
            stop_reason = "no_forward_successor"
        else:
            # Advance only through a retained NX(UR(...)) observable outcome.
            candidates = control.forward_successors
            _pattern, selected_event, next_state = candidates[iteration % len(candidates)]

        stats.append(
            ProductIterationStats(
                iteration=iteration,
                current=current,
                local_state_count=len(local_states),
                decision_estimate_state_count=counts[0],
                observation_estimate_state_count=counts[1],
                decision_information_state_count=counts[2],
                observation_information_state_count=counts[3],
                new_state_count=new_state_count,
                cumulative_state_count=len(cumulative_states),
                local_edge_count=counts[4],
                selected_event=selected_event,
                next_state=next_state,
                cache_hit=cache_hit,
                step_seconds=perf_counter() - step_start,
                construction_strategy=strategy,
                synthesis_passes=synthesis_passes,
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
        cycle_check=cycle_check,
        stop_reason=stop_reason,
        pattern_mode=pattern_mode,
        synthesis_calls=synthesis_calls,
        cache_hits=cache_hits,
        successor_policy="round-robin",
    )


def verify_case1_product_cycle(product: ImplicitProductDFA) -> ProductCycleCheck:
    current = product.initial
    required_events = ("o2", "b", "a")
    path: list[tuple[ProductState, Event, ProductState]] = []

    for component_event in required_events:
        target = product.component.transitions.get((current[0], component_event))

        if target is None:
            return ProductCycleCheck(
                ok=False,
                path=tuple(path),
                message=(
                    "could not lift the component q_0 --o2--> q_1 --b--> q_2 "
                    "--a--> q_0 cycle into the product"
                ),
            )

        next_state = list(current)
        next_state[0] = target
        event = _product_event(0, component_event)
        successor = tuple(next_state)
        path.append((current, event, successor))
        current = successor

    if current != product.initial:
        return ProductCycleCheck(
            ok=False,
            path=tuple(path),
            message="lifted component cycle did not return to the product initial state",
        )

    return ProductCycleCheck(
        ok=True,
        path=tuple(path),
        message=(
            "verified decision-observation cycle: "
            + " -> ".join(
                f"{product_state_label(source)} --{event}--> {product_state_label(target)}"
                for source, event, target in path
            )
        ),
    )


def _case1_single_branch_successor(
    product: ImplicitProductDFA,
    state: ProductState,
    iteration: int,
) -> tuple[Event | None, ProductState | None]:
    if not state:
        return None, None

    component_order = list(range(product.copies))
    shift = iteration % product.copies
    component_order = component_order[shift:] + component_order[:shift]

    for index in component_order:
        component_event = _preferred_component_event(state[index], iteration // max(product.copies, 1))

        if component_event is None:
            continue

        target = product.component.transitions.get((state[index], component_event))

        if target is None:
            continue

        next_state = list(state)
        next_state[index] = target

        return _product_event(index, component_event), tuple(next_state)

    enabled = product.enabled(state)

    return enabled[iteration % len(enabled)] if enabled else (None, None)


def _preferred_component_event(state: State, cycle_index: int) -> Event | None:
    if state == "q_0":
        return "o2"

    if state == "q_1":
        return "o1" if cycle_index % 3 == 2 else "b"

    if state == "q_2":
        return "a"

    if state == "q_3":
        return "b"

    return None


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

