"""Independent replication of Tatsumoto et al., CEP 81 (2018), pp. 97--104.

This module operates on known component states under full observation.
It does not invoke BTS, LL-BTS, Q_f/Q_e structural analysis, or their safety
checks. Paper equations and component-window interpretations are exposed
separately, since the printed numerical examples need to be checked against
the extra global truncation in the equations.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from time import perf_counter

from des_core.automata import DFA


class WarehouseBudgetExceeded(RuntimeError):
    """An incomplete calculation; it is not a losing synthesis result."""


@dataclass
class WarehouseResult:
    status: str
    horizon: int
    interpretation: str
    attitude: str
    initial: tuple
    window: DFA
    retained_states: frozenset
    retained_marked: frozenset
    gamma_c: frozenset
    local_state_counts: tuple
    component_product_states: int
    window_transitions: int
    retained_transitions: int
    seconds: float
    removed_states: int


def reachable(plant, initial=None, allowed=None):
    q0 = plant.initial if initial is None else initial
    allowed = plant.states if allowed is None else allowed

    if q0 not in allowed:
        return frozenset()

    seen = {q0}
    queue = deque([q0])

    while queue:
        q = queue.popleft()

        for _, target in plant.enabled(q):
            if target in allowed and target not in seen:
                seen.add(target)
                queue.append(target)

    return frozenset(seen)


def exact_depth_states(plant, q0, depth):
    """Endpoints of length-depth strings, including repeated cyclic states."""

    frontier = {q0}

    for _ in range(depth):
        frontier = {target for q in frontier for _, target in plant.enabled(q)}

    return frozenset(frontier)


def truncate(plant, marked, q0, horizon):
    """Paper f^N: induced transition relation on states reachable within N."""

    if horizon < 0:
        raise ValueError('truncation depth must be nonnegative')

    distance = {q0: 0}
    queue = deque([q0])

    while queue:
        q = queue.popleft()

        if distance[q] >= horizon:
            continue

        for _, target in plant.enabled(q):
            if target not in distance:
                distance[target] = distance[q] + 1
                queue.append(target)

    states = frozenset(distance)
    transitions = {(q, event): target for q in states for event, target in plant.enabled(q)
                   if target in states}
    events = frozenset(event for _, event in transitions)
    window = DFA(states, q0, events, plant.controllable & events, events, transitions)

    return window, marked & states


def synchronous_product(components, *, max_states=200_000):
    """Reachable synchronous product, retaining original event ownership."""

    plants = [component[0] for component in components]
    marked = [component[1] for component in components]
    initial = tuple(plant.initial for plant in plants)
    events = frozenset().union(*(plant.events for plant in plants))
    controllable = frozenset(event for event in events
                             if all(event not in plant.events or event in plant.controllable for plant in plants))
    owners = {event: tuple(i for i, plant in enumerate(plants) if event in plant.events) for event in events}
    transitions = {}
    seen = {initial}
    queue = deque([initial])

    while queue:
        q = queue.popleft()

        for event in sorted(events):
            if not all((q[i], event) in plants[i].transitions for i in owners[event]):
                continue

            target = tuple(plants[i].transitions[q[i], event] if i in owners[event] else q[i]
                           for i in range(len(plants)))
            transitions[q, event] = target

            if target not in seen:
                seen.add(target)

                if len(seen) > max_states:
                    raise WarehouseBudgetExceeded(f'product exceeds {max_states} states')

                queue.append(target)

    states = frozenset(seen)
    goal = frozenset(q for q in states if all(q[i] in marked[i] for i in range(len(plants))))

    return DFA(states, initial, events, controllable, events, transitions), goal


def supremal_controllable_nonblocking(plant, marked, legal):
    """Standard full-observation controllability/coreachability fixed point.

    The specification is a state-deletion subautomaton with all legal states
    marked, as in the paper's warehouse application. Its synchronous product
    with the plant retains the plant's marking. No deadlock-free test is added:
    a marked terminal state is permitted to have no outgoing transition.
    """

    retained = set(legal)
    predecessors = defaultdict(set)

    for (q, _), target in plant.transitions.items():
        predecessors[target].add(q)

    while True:
        coreachable = set(marked & retained)
        queue = deque(coreachable)

        while queue:
            target = queue.popleft()

            for q in predecessors[target] & retained:
                if q not in coreachable:
                    coreachable.add(q)
                    queue.append(q)

        updated = {q for q in coreachable
                   if all(event in plant.controllable or target in coreachable
                          for event, target in plant.enabled(q))}

        if updated == retained:
            break

        retained = updated

    retained = reachable(plant, allowed=frozenset(retained))

    return retained, marked & retained


def solve_warehouse(components, *, horizon=3, legal=lambda q: True,
                    attitude='optimistic', interpretation='equations', max_states=200_000):
    """Paper steps 1--5; return the next enabled controllable events.

    equations: apply f^N (or f^(N-1)) to the component-window product,
    then mark length-N endpoints, exactly as the displayed formulas say.
    component-frontiers: keep that product and mark the product of local
    boundary/goal sets. This separate reading is tested against the paper's
    reported example counts; it is never silently substituted for equations.
    """

    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError('lookahead horizon must be a positive integer')

    if attitude not in ('optimistic', 'conservative'):
        raise ValueError(attitude)

    if interpretation not in ('equations', 'component-frontiers'):
        raise ValueError(interpretation)

    for plant, _ in components:
        if plant.observable != plant.events:
            raise ValueError('the 2018 method requires known component states; use a fully observed comparison copy')

    started = perf_counter()
    local = [truncate(plant, marked, plant.initial, horizon) for plant, marked in components]

    if interpretation == 'component-frontiers' and attitude == 'optimistic':
        local = [(plant, marked | exact_depth_states(plant, plant.initial, horizon)) for plant, marked in local]

    product, marked = synchronous_product(local, max_states=max_states)
    product_count = len(product.states)

    if interpretation == 'equations':
        depth = horizon if attitude == 'optimistic' else horizon - 1
        product, marked = truncate(product, marked, product.initial, depth)

        if attitude == 'optimistic':
            marked = marked | exact_depth_states(product, product.initial, horizon)
    elif attitude == 'conservative':
        local = [truncate(plant, marked, plant.initial, horizon - 1) for plant, marked in local]
        product, marked = synchronous_product(local, max_states=max_states)

    allowed = frozenset(q for q in product.states if legal(q))
    retained, retained_marked = supremal_controllable_nonblocking(product, marked, allowed)
    gamma_c = frozenset(event for event, target in product.enabled(product.initial)
                        if event in product.controllable and target in retained) if product.initial in retained else frozenset()
    retained_transitions = sum(q in retained and target in retained for (q, _), target in product.transitions.items())

    return WarehouseResult('local_supervisor' if product.initial in retained else 'empty_local_supervisor',
        horizon, interpretation, attitude, product.initial, product, retained, retained_marked, gamma_c,
        tuple(len(plant.states) for plant, _ in local), product_count, len(product.transitions),
        retained_transitions, perf_counter() - started, len(product.states) - len(retained))
