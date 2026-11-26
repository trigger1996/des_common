"""Independent finite-horizon LLP of Chung, Lafortune and Lin (TAC 1992).

Source DOI: 10.1109/9.182478, Section II, blocks 1--5. The optimistic
boundary is legal/marked; the conservative boundary is illegal. A backward
controllability/nonblocking pass supplies the first-event control pattern.
Only fully observed, state-based prefix safety specifications are supported.
Occurrences with the same (physical state, depth) may share one calculation:
they have identical residual plant and legality, unlike different depths.
There is no call to our LL-BTS, structural analysis, or deadlock liveness test.
"""

from dataclasses import dataclass
from time import perf_counter


class ClassicLLPBudgetExceeded(RuntimeError):
    """A computation limit is not nonexistence of a supervisor."""


@dataclass
class ClassicLLPResult:
    status: str
    horizon: int
    attitude: str
    initial: object
    gamma_c: frozenset
    stored_states: int
    stored_transitions: int
    retained_states: int
    removed_states: int
    physical_states: int
    seconds: float
    shared_same_depth: bool


def solve_classic_llp(plant, *, horizon, legal=lambda q: True, marked=None,
                      initial=None, attitude='optimistic', share_same_depth=True,
                      max_states=200_000):
    """Build an N-level projection and solve its controllable marked language.

    Marking a legal interior state allows stopping there, as in the published
    nonblocking objective. Do not insert our enabled-event availability test.
    Root failure is a local empty-language result, not global losing.
    share_same_depth=False materializes every event-prefix occurrence and is
    used as an independent conformance reference on small windows.
    """

    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError('horizon must be a positive integer')

    if plant.observable != plant.events:
        raise ValueError('LLP-1992 comparison requires full observation')

    if attitude not in ('optimistic', 'conservative'):
        raise ValueError(attitude)

    started = perf_counter()
    initial = plant.initial if initial is None else initial
    marked = plant.states if marked is None else frozenset(marked)
    layers = [[] for _ in range(horizon + 1)]
    physical = [initial]
    allowed = [bool(legal(initial))]
    transitions = [[]]
    layers[0].append(0)
    index = {(initial, 0): 0}

    for depth in range(horizon):
        for source in layers[depth]:
            if not allowed[source]:
                continue

            for event, q_next in plant.enabled(physical[source]):
                key = q_next, depth + 1
                target = index.get(key) if share_same_depth else None

                if target is None:
                    if len(physical) >= max_states:
                        raise ClassicLLPBudgetExceeded(f'projection exceeds {max_states} states')

                    target = len(physical)
                    index[key] = target
                    physical.append(q_next)
                    allowed.append(bool(legal(q_next)))
                    transitions.append([])
                    layers[depth + 1].append(target)

                transitions[source].append((event, target))

    good = [False] * len(physical)

    for depth in range(horizon, -1, -1):
        for source in layers[depth]:
            if not allowed[source]:
                continue

            if depth == horizon:
                good[source] = attitude == 'optimistic'

                continue

            outcomes = transitions[source]
            uncontrollable_safe = all(good[target] for event, target in outcomes
                                      if event in plant.uncontrollable)
            can_mark = physical[source] in marked or any(good[target] for _, target in outcomes)
            good[source] = uncontrollable_safe and can_mark

    gamma_c = frozenset(event for event, target in transitions[0]
                        if event in plant.controllable and good[target]) if good[0] else frozenset()
    retained = sum(good)

    return ClassicLLPResult('local_supervisor' if good[0] else 'empty_local_supervisor',
        horizon, attitude, initial, gamma_c, len(physical), sum(map(len, transitions)),
        retained, len(physical) - retained, len(set(physical)),
        perf_counter() - started, share_same_depth)
