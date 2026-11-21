"""Traditional BTS construction for a fully known, partially observed DFA.

Enumerate every admissible pattern, perform complete UR/NX, then prune the
constructed BTS. No lookahead window and no Qf/Qe certificates are used.
"""

from collections import defaultdict, deque
from itertools import combinations
from time import perf_counter

from des_core.certified_lookahead import Choice, Bipartitle_System


class BTSBudgetExceeded(RuntimeError):
    def __init__(self, reason, **metrics):
        super().__init__(reason)
        self.metrics = dict(reason=reason, **metrics)


def traditional_ur(plant, estimate, pattern):
    """UR_pattern(estimate): zero or more enabled unobservable transitions.

    pattern contains the controllable events selected by the supervisor.
    Uncontrollable events are always enabled. This is a full fixed point,
    independent of any lookahead window; hidden cycles are visited once.
    """

    enabled = pattern|plant.uncontrollable
    initial = frozenset(estimate)
    closure = set(initial);queue = deque(initial)

    while queue:
        q = queue.popleft()

        for event, target in plant.enabled(q):
            if event in enabled and event not in plant.observable and target not in closure:
                closure.add(target);queue.append(target)

    return frozenset(closure)


def traditional_nx(plant, states, observable_event):
    """NX_event(states): exactly ONE transition labelled observable_event.

    states is usually the preceding UR result. This function neither computes
    UR nor follows another observable event afterwards. It can return multiple
    states because different possible source states share the same event.
    The caller decides whether this observable event is enabled by its pattern.
    """

    if observable_event not in plant.observable:
        raise ValueError('NX requires one event from the observable alphabet')

    return frozenset(target for q in states for event, target in plant.enabled(q)
                     if event == observable_event)


def _traditional_nx_all(plant, states, enabled):
    """Batch the separate NX_event(states) sets in one outgoing-edge scan.

    Each dictionary entry represents its own single observable event. Keeping
    this batch avoids rescanning every transition once per observable symbol.
    """

    nx = defaultdict(set)

    for q in states:
        for event, target in plant.enabled(q):
            if event in enabled and event in plant.observable:nx[event].add(target)

    return tuple((event, frozenset(targets)) for event, targets in sorted(nx.items()))


def traditional_ur_nx(plant, estimate, pattern):
    """One BTS choice: first full UR, then each enabled single-event NX.

    The next decision estimate is NX_event(UR_pattern(estimate)); its next UR
    is computed only after choosing the next control pattern.
    """

    closure = traditional_ur(plant, estimate, pattern)
    successors = _traditional_nx_all(plant, closure, pattern|plant.uncontrollable)

    return Choice(pattern, closure, successors)


def construct_offline_bts(plant, estimate=None, *, max_choices=None,
                          max_decisions=None, timeout_seconds=None):
    started = perf_counter()
    initial = frozenset((plant.initial,)) if estimate is None else frozenset(estimate)
    events = tuple(sorted(plant.controllable))
    queue = deque((initial,));seen = {initial};choices = {};valid = {};tested = 0

    def check():
        elapsed = perf_counter()-started
        reason = ('choice budget exceeded' if max_choices is not None and tested >= max_choices else
                'decision budget exceeded' if max_decisions is not None and len(seen)>max_decisions else
                'time budget exceeded' if timeout_seconds is not None and elapsed >= timeout_seconds else None)

        if reason:raise BTSBudgetExceeded(reason, seconds=elapsed, patterns_tested=tested,
            decision_estimates_discovered=len(seen), decision_estimates_completed=len(choices),
            control_pattern_count=2**len(events), complete=False)

    # Build first, including locally deadlocking/unsafe patterns. Such patterns
    # and their reachable observations remain visible in the unpruned BTS.
    while queue:
        x = queue.popleft();options = [];flags = []

        for size in range(len(events)+1):
            for combo in combinations(events, size):
                check();pattern = frozenset(combo)
                choice = traditional_ur_nx(plant, x, pattern);tested += 1
                enabled = pattern|plant.uncontrollable
                flags.append(all(any(e in enabled for e, _ in plant.enabled(q)) for q in choice.closure))
                options.append(choice)

                for _, target in choice.successors:
                    if target not in seen:seen.add(target);queue.append(target)

        choices[x] = tuple(options);valid[x] = flags

    # Greatest fixed point, implemented with linear count updates for both
    # solvers. This avoids attributing a pruning-implementation difference to u.
    incoming = defaultdict(list);remaining = {};removed = set()

    for x, options in choices.items():
        remaining[x] = sum(valid[x])

        for i, c in enumerate(options):
            if not valid[x][i]:removed.add((x, i));continue

            for target in {target for _, target in c.successors}:incoming[target].append((x, i))

    lost = {x for x, count in remaining.items() if not count};queue = deque(lost)

    while queue:
        target = queue.popleft()

        for x, i in incoming[target]:
            if (x, i) in removed:continue

            removed.add((x, i));remaining[x] -= 1

            if remaining[x] == 0 and x not in lost:lost.add(x);queue.append(x)

    policy = {x:tuple(c for i, c in enumerate(options) if (x, i) not in removed)
            for x, options in choices.items() if x not in lost}
    observations = {(c.closure, c.pattern) for options in choices.values() for c in options}
    d_edges = {(x, c.closure, c.pattern) for x, options in choices.items() for c in options}
    o_edges = {(c.closure, c.pattern, e, y) for options in choices.values() for c in options for e, y in c.successors}

    return Bipartitle_System('winning' if initial in policy else 'losing', initial, None,
        frozenset(plant.states), policy, frozenset(), len(choices), len(observations),
        len(d_edges)+len(o_edges), 0, perf_counter()-started, plant.controllable, choices)
