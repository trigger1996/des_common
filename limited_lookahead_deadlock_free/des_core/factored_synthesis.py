"""Algorithm 2 over exact families of controllable observable choices.

For fixed UR and hidden choice, enabling a controllable observable event only
adds its O->D outcomes. The largest safe observable choice contains exactly
the events whose local successors all survive. Uncontrollable outcomes remain
mandatory. See the consistency notes for the fixed-point argument.
"""

from collections import defaultdict, deque


def synthesize_factored_controls(plant, current, result):
    # Local imports avoid a module import cycle with the public result type.
    from des_core.ll_bts import _maximal_patterns
    from des_core.ll_bts_synthesis import LLBTSControlResult

    if result._compact_graph is not None:
        return result._compact_graph.synthesize()

    window = result.lookahead_states
    adjacency = {q: tuple(plant.enabled(q)) for q in window}
    observable = plant.observable
    controlled_observable = plant.controllable & observable
    mandatory_observable = plant.uncontrollable & observable
    estimates = {x for _root, x in result.decision_states}
    deadlocks = {q for q, edges in adjacency.items() if not edges}
    losing_d = {x for x in estimates if not x.isdisjoint(deadlocks)}
    losing_o = set()
    incoming_controls = defaultdict(list)
    incoming_outcomes = defaultdict(list)
    remaining = {}
    allowed = {}
    targets_by_o = {}

    for estimate in estimates:
        choices = result.control_choices.get(estimate, ())
        remaining[estimate] = len(choices)

        if not choices:
            losing_d.add(estimate)

        for observation in choices:
            incoming_controls[observation].append(estimate)

    for observation in result.observation_states:
        estimate, upper = observation
        fixed_enabled = (upper - observable) | plant.uncontrollable
        targets = defaultdict(set)
        occurs = set()

        for q in estimate:
            edges = adjacency[q]

            for event, target in edges:
                if event in observable:
                    occurs.add(event)

                    if target in window:
                        targets[event].add(target)

        successors = {e: frozenset(qs) for e, qs in targets.items()}
        enabled = set(upper & controlled_observable)
        invalid = not estimate or not estimate.isdisjoint(deadlocks)

        for event in occurs:
            successor = successors.get(event)

            if not successor:
                continue

            if successor not in estimates or successor in losing_d:
                if event in mandatory_observable:
                    invalid = True
                else:
                    enabled.discard(event)
            else:
                incoming_outcomes[successor].append((observation, event))

        allowed[observation] = enabled
        targets_by_o[observation] = successors

        if invalid:
            losing_o.add(observation)

    queue = deque([('D', x) for x in losing_d] + [('O', o) for o in losing_o])

    while queue:
        kind, node = queue.popleft()

        if kind == 'O':
            for estimate in incoming_controls[node]:
                if estimate in losing_d:
                    continue

                remaining[estimate] -= 1

                if remaining[estimate] == 0:
                    losing_d.add(estimate)
                    queue.append(('D', estimate))

            continue

        for observation, event in incoming_outcomes[node]:
            if observation in losing_o:
                continue

            enabled = allowed[observation]

            if event in mandatory_observable:
                invalid = True
            else:
                enabled.discard(event)
                invalid = False

            if invalid:
                losing_o.add(observation)
                queue.append(('O', observation))

    initial = frozenset({current})

    if initial not in estimates or initial in losing_d:
        return LLBTSControlResult(True, (), ())

    survivors = [o for o in result.control_choices.get(initial, ()) if o not in losing_o]
    patterns_by_o = {o: (o[1] - observable) | frozenset(allowed[o]) for o in survivors}
    maximal = _maximal_patterns(patterns_by_o.values())
    maximal_set = set(maximal)
    forward = set()

    for observation, pattern in patterns_by_o.items():
        if pattern not in maximal_set:
            continue

        for event, successor in targets_by_o[observation].items():
            if event in pattern or event in mandatory_observable:
                for root in successor:
                    forward.add((pattern, event, root))

    return LLBTSControlResult(False, maximal, tuple(sorted(
        forward, key=lambda item: (len(item[0]), sorted(item[0]), item[1], item[2])
    )))
