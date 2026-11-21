"""Exact maximal representatives for control choices in a fixed local window.

See OPTIMIZATION_AND_CONSISTENCY_NOTES.md for the dominance argument. This
reduces the represented graph, not the plant or its event partitions.
"""

from collections import deque
from itertools import combinations


def representative_choices(plant, seeds, window, adjacency, *, factor_observable=False):
    """Yield (UR estimate, controllable pattern) without a global powerset.

    Hidden events that would enlarge UR are branched on demand. For a completed
    UR, all hidden events preserving it are enabled in its unique largest hidden
    choice. Observable events absent from UR are likewise always enabled.
    Observable boundary events MUST still be enumerated for consistency (ii).
    """

    hidden = plant.controllable - plant.observable
    observable_control = plant.controllable & plant.observable
    mandatory = plant.uncontrollable - plant.observable
    seen_estimates = set()
    stack = [(frozenset(), frozenset())]

    while stack:
        enabled, disabled = stack.pop()
        reached = set(seeds)
        queue = deque(seeds)

        while queue:
            for event, target in adjacency[queue.popleft()]:
                if (event in mandatory or event in enabled) and target in window and target not in reached:
                    reached.add(target)
                    queue.append(target)

        unknown = {
            event for state in reached for event, target in adjacency[state]
            if event in hidden and event not in enabled and event not in disabled
            and target in window and target not in reached
        }

        if unknown:
            event = min(unknown)
            stack.append((enabled, disabled | {event}))
            stack.append((enabled | {event}, disabled))

            continue

        estimate = frozenset(reached)

        if estimate in seen_estimates:
            continue

        seen_estimates.add(estimate)
        forbidden_hidden = {
            event for state in reached for event, target in adjacency[state]
            if event in hidden and target in window and target not in reached
        }
        relevant_observable = sorted({
            event for state in reached for event, _target in adjacency[state]
            if event in observable_control
        })
        base = plant.controllable - forbidden_hidden - set(relevant_observable)

        if factor_observable:
            # One family represents every subset of controllable observable
            # events. Algorithm 2 will remove exactly the unsafe observable
            # choices, instead of materializing their powerset here.
            upper = base | frozenset(relevant_observable)
            # Apply locally decidable Algorithm-2 losses before expanding a
            # family. Missing uncontrollable outcomes cannot be repaired by
            # future backward pruning. Missing controllable outcomes can only
            # be disabled. If even the largest remaining pattern deadlocks a
            # concrete state, no member of this family can survive.
            occurs = set()
            local = set()

            for state in reached:
                for event, target in adjacency[state]:
                    if event in plant.observable:
                        occurs.add(event)

                        if target in window:
                            local.add(event)

            missing = occurs - local

            if missing & plant.uncontrollable:
                continue

            upper = upper - missing
            enabled_full = upper | plant.uncontrollable

            if any(not any(event in enabled_full for event, _target in adjacency[state])
                   for state in reached):
                continue

            yield estimate, upper

            continue

        for size in range(len(relevant_observable) + 1):
            for subset in combinations(relevant_observable, size):
                yield estimate, base | frozenset(subset)
