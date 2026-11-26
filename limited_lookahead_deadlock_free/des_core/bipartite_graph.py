"""Explicit bipartite graphs with decision states (q_hat, x_hat).

UR/NX fragments may reuse an estimate-level calculation, but decision states
with different q_hat values are distinct stored dictionary keys. Observation
updates branch to every q_hat in the successor estimate. The supervisor's
estimate-level policy remains shared to enforce partial-observation consistency.
"""

from collections import deque


def observation_key(choice):
    return choice.closure, choice.pattern


def choice_variants(value):
    return value if isinstance(value, tuple) else (value,)


def attach_pair_graph(result, *, analysis_state=None, record_steps=False):
    """Construct the actual pair-valued graph and its retained subgraph."""

    initial_q = min(result.initial) if analysis_state is None else analysis_state

    if initial_q not in result.initial:
        raise ValueError('initial analysis state must belong to the initial estimate')

    initial = (initial_q, result.initial)
    queue = deque([initial])
    seen = {initial}
    decisions = {}
    observations = {}
    steps = []
    control_transitions = 0

    while queue:
        decision = queue.popleft()
        q_hat, x_hat = decision
        options = result.constructed_choices.get(x_hat, ())
        decisions[decision] = options

        for choice in options:
            control_transitions += 1
            key = observation_key(choice)
            new_variant = False

            if key not in observations:
                observations[key] = choice
                new_variant = True
            elif choice not in choice_variants(observations[key]):
                observations[key] = choice_variants(observations[key]) + (choice,)
                new_variant = True

            targets = []

            # An observation state is shared by incoming control transitions.
            # Its outgoing transitions are expanded once, while EVERY source
            # decision pair and its control transition remain stored separately.
            if new_variant:
                for event, x_hat_next in choice.successors:
                    for q_hat_next in sorted(x_hat_next):
                        target = (q_hat_next, x_hat_next)
                        targets.append((event, target))

                        if target not in seen:
                            seen.add(target)
                            queue.append(target)

            if record_steps:
                steps.append(dict(operation='construct_pattern', decision=decision,
                                  choice=choice, targets=tuple(targets),
                                  reused_observation=not new_variant))

    observation_transitions = 0

    for value in observations.values():
        variants = choice_variants(value)

        if len(variants) == 1:
            observation_transitions += sum(len(x) for _, x in variants[0].successors)
        else:
            observation_transitions += len({(event, (q, x)) for c in variants
                                           for event, x in c.successors for q in x})

    retained = {}
    reachable = set()
    retained_observations = set()

    if result.status == 'winning':
        queue = deque([initial])
        reachable.add(initial)

        while queue:
            decision = queue.popleft()
            options = result.policy.get(decision[1], ())
            retained[decision] = options

            for choice in options:
                key = observation_key(choice)

                if key in retained_observations:
                    continue

                retained_observations.add(key)

                for _, x_hat_next in choice.successors:
                    for q_hat_next in x_hat_next:
                        target = (q_hat_next, x_hat_next)
                        assert target in decisions

                        if target not in reachable:
                            reachable.add(target)
                            queue.append(target)

    result.initial_decision = initial
    result.decision_states = decisions
    result.observation_states = observations
    result.decision_policy = retained
    result.policy = {pair[1]: choices for pair, choices in retained.items()}
    result.decision_count = len(decisions)
    result.observation_count = len(observations)
    result.edge_count = control_transitions + observation_transitions
    result.construction_steps = steps
    result.representation = '(q_hat, x_hat) decision states; (x, gamma) observation states'

    if record_steps:
        for decision, choices in decisions.items():
            for choice in choices:
                if decision not in retained or choice not in retained[decision]:
                    steps.append(dict(operation='prune_pattern', decision=decision, choice=choice))

        for decision in decisions:
            if decision not in retained:
                steps.append(dict(operation='prune_decision', decision=decision))

    return result


def retained_decision_count(result):
    return len(result.decision_policy)
