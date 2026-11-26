"""Example-local BFS construction with immediate branch dominance merging.

Different (q_hat, x_hat) decision states are never merged. The optional rule
compares D-O-D fragments at the SAME source decision, keeping a larger
control pattern only when the hidden reach and every labeled successor agree.
No general solver or other example enables this rule.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import combinations
import json
from pathlib import Path
from time import perf_counter

from des_core.certified_lookahead import Bipartitle_System, complete_choice, limited_choice


def ordered(values):
    return sorted(values, key=lambda q: int(q.split('_')[-1]))


@dataclass(frozen=True)
class Fragment:
    choice: object
    actual: object
    live: bool
    avoid_bad: bool

    @property
    def complete(self):
        return self.choice == self.actual

    @property
    def eligible(self):
        return self.complete and self.live and self.avoid_bad

    @property
    def boundary(self):
        return self.live and self.avoid_bad and not self.complete


def equivalent_fragment(first, second):
    """Preserve full labeled NX outcomes and safety, not just target names."""

    return (first.choice.closure == second.choice.closure
            and first.choice.successors == second.choice.successors
            and first.actual.closure == second.actual.closure
            and first.actual.successors == second.actual.successors
            and first.live == second.live and first.avoid_bad == second.avoid_bad
            and first.complete == second.complete)


def merge_at_insertion(active, fragment):
    """Mutate one source's branches immediately, before the next pattern.

    Return (discarded fragment, kept fragment) pairs. Incomparable controls
    remain separate. The caller records each insertion and each merge.
    """

    changes = []

    for other in list(active.values()):
        if other == fragment or not equivalent_fragment(other, fragment):
            continue

        if other.choice.pattern < fragment.choice.pattern:
            active.pop(other.choice)
            changes.append((other, fragment))
        elif fragment.choice.pattern < other.choice.pattern:
            active.pop(fragment.choice)
            changes.append((fragment, other))

            break

    return changes


class ExampleConstruction:
    def __init__(self, pre, horizon, *, merge=False):
        if not isinstance(horizon, int) or horizon < 1:
            raise ValueError('horizon must be a positive integer')

        source = Path(__file__).with_name('plant.json')
        model = json.loads(source.read_text(encoding='utf-8'))
        plant = pre.plant
        assert plant.states == frozenset(model['states'])
        assert plant.initial == model['initial']
        assert plant.controllable == frozenset(model['controllable'])
        assert plant.observable == frozenset(model['observable'])
        assert dict(plant.transitions) == {(q, e): target for q, e, target in model['transitions']}
        self.pre = pre
        self.plant = plant
        self.horizon = horizon
        self.merge = merge
        self.initial = (plant.initial, frozenset({plant.initial}))
        self.ids = {}
        self.oids = {}
        self.alive = set()
        self.branches = defaultdict(dict)
        self.history = []
        self.fragment_cache = {}
        self.windows = {}
        self.merge_count = 0
        self.tested = 0
        self.generated_branches = 0

    def decision_id(self, decision):
        if decision not in self.ids:
            self.ids[decision] = 'D' + str(len(self.ids))
            self.alive.add(decision)

        return self.ids[decision]

    def observation_id(self, choice):
        key = choice.closure, choice.pattern

        if key not in self.oids:
            self.oids[key] = 'O' + str(len(self.oids))

        return self.oids[key]

    def record(self):
        decisions = [dict(id=self.ids[pair], q_hat=pair[0], estimate=ordered(pair[1]),
                          state=[pair[0], ordered(pair[1])], retained=True,
                          safe_terminal=bool(pair[1]) and pair[1] <= self.pre.Q_e)
                     for pair in self.ids if pair in self.alive]
        observations = {}
        transitions = set()

        for pair in self.ids:
            if pair not in self.alive:
                continue

            for fragment in self.branches[pair].values():
                choice = fragment.choice
                oid = self.observation_id(choice)
                observations[oid] = dict(id=oid, estimate=ordered(choice.closure),
                    pattern_controllable=sorted(choice.pattern),
                    pattern_full=sorted(choice.pattern | self.plant.uncontrollable),
                    retained=True, locally_executable=fragment.eligible)
                transitions.add((self.ids[pair], oid, ','.join(sorted(choice.pattern)) or '{}'))

                for event, estimate in choice.successors:
                    for q_hat in estimate:
                        target = (q_hat, estimate)

                        if target in self.alive:
                            transitions.add((oid, self.ids[target], event))

        return dict(D=decisions, O=list(observations.values()), edges=sorted(transitions),
                    initial=self.ids[self.initial])

    def save(self, operation, **details):
        snapshot = self.record()
        self.history.append(dict(step=len(self.history), operation=operation, details=details,
                                 **snapshot))

    def window(self, estimate):
        if estimate not in self.windows:
            states = set(estimate)
            frontier = set(estimate)

            for _ in range(self.horizon):
                frontier = {target for q in frontier for _, target in self.plant.enabled(q)} - states
                states.update(frontier)

            self.windows[estimate] = frozenset(states)

        return self.windows[estimate]

    def fragment(self, estimate, pattern):
        key = estimate, pattern

        if key not in self.fragment_cache:
            choice = limited_choice(self.plant, estimate, pattern, self.window(estimate))
            actual = complete_choice(self.plant, estimate, pattern)
            gamma = pattern | self.plant.uncontrollable
            live = all(any(event in gamma for event, _ in self.plant.enabled(q)) for q in actual.closure)
            avoid_bad = not bool(actual.closure & (self.pre.Q_d | self.pre.Q_f))
            self.fragment_cache[key] = Fragment(choice, actual, live, avoid_bad)
            self.tested += 1

        return self.fragment_cache[key]

    def construct(self):
        self.decision_id(self.initial)
        self.save('initial_decision')
        queue = deque([self.initial])
        seen = {self.initial}
        events = sorted(self.plant.controllable)

        while queue:
            decision = queue.popleft()
            estimate = decision[1]

            if estimate & (self.pre.Q_d | self.pre.Q_f) or estimate <= self.pre.Q_e:
                self.save('stop_expanding_decision', decision=self.ids[decision])

                continue

            for size in range(len(events) + 1):
                for enabled in combinations(events, size):
                    fragment = self.fragment(estimate, frozenset(enabled))
                    choice = fragment.choice
                    self.branches[decision][choice] = fragment
                    self.observation_id(choice)
                    self.generated_branches += 1

                    for _, successor in choice.successors:
                        for q_hat in ordered(successor):
                            target = q_hat, successor
                            self.decision_id(target)

                            if target not in seen:
                                seen.add(target)
                                queue.append(target)

                    self.save('construct_pattern', decision=self.ids[decision],
                              observation=self.observation_id(choice), gamma_c=sorted(choice.pattern),
                              eligible=fragment.eligible, boundary=fragment.boundary)

                    if self.merge:
                        for discarded, kept in merge_at_insertion(self.branches[decision], fragment):
                            self.merge_count += 1
                            self.save('merge_pattern', decision=self.ids[decision],
                                      discarded=self.observation_id(discarded.choice),
                                      kept=self.observation_id(kept.choice),
                                      smaller_gamma_c=sorted(discarded.choice.pattern),
                                      larger_gamma_c=sorted(kept.choice.pattern),
                                      reason='Same source, UR and labeled decision successors; strict control inclusion.')

        self.save('construction_complete', merge_count=self.merge_count)

    def optimistic_lost(self, raw):
        counts = {pair: sum(fragment.eligible or fragment.boundary for fragment in options.values())
                  for pair, options in raw.items()}
        safe = {pair for pair in raw if pair[1] <= self.pre.Q_e}
        incoming = defaultdict(list)

        for pair, options in raw.items():
            for choice, fragment in options.items():
                if not fragment.eligible:
                    continue

                for _, estimate in choice.successors:
                    for q_hat in estimate:
                        incoming[q_hat, estimate].append((pair, choice))

        lost = {pair for pair, count in counts.items() if not count and pair not in safe}
        queue = deque(lost)
        removed = set()

        while queue:
            target = queue.popleft()

            for pair, choice in incoming[target]:
                if (pair, choice) in removed:
                    continue

                removed.add((pair, choice))
                counts[pair] -= 1

                if not counts[pair] and pair not in safe and pair not in lost:
                    lost.add(pair)
                    queue.append(pair)

        return lost

    def delete_branch(self, pair, choice, reason):
        if choice in self.branches[pair]:
            self.branches[pair].pop(choice)
            self.save('prune_pattern', decision=self.ids[pair], observation=self.observation_id(choice), reason=reason)

    def prune(self, raw):
        counts = {pair: sum(fragment.eligible for fragment in options.values()) for pair, options in raw.items()}
        safe = {pair for pair in raw if pair[1] <= self.pre.Q_e}
        incoming = defaultdict(list)

        for pair, options in raw.items():
            for choice, fragment in options.items():
                if not fragment.eligible:
                    self.delete_branch(pair, choice, 'Incomplete fragment or deadlock/liveness violation')

                    continue

                for _, estimate in choice.successors:
                    for q_hat in estimate:
                        incoming[q_hat, estimate].append((pair, choice))

        lost = {pair for pair, count in counts.items() if not count and pair not in safe}
        queue = deque(sorted(lost, key=lambda pair: self.ids[pair]))

        while queue:
            target = queue.popleft()

            for pair, choice in incoming[target]:
                if choice not in self.branches[pair]:
                    continue

                self.delete_branch(pair, choice, 'A required observation successor was removed')
                counts[pair] -= 1

                if not counts[pair] and pair not in lost and pair not in safe:
                    lost.add(pair)
                    queue.append(pair)

            self.alive.discard(target)
            self.save('prune_decision', decision=self.ids[target])

        status = 'winning' if self.initial in self.alive else (
            'losing' if self.initial in self.optimistic_lost(raw) else 'inconclusive')
        reachable = set()
        queue = deque([self.initial] if status == 'winning' else [])

        while queue:
            pair = queue.popleft()

            if pair in reachable:
                continue

            reachable.add(pair)

            for choice in self.branches[pair]:
                for _, estimate in choice.successors:
                    queue.extend((q_hat, estimate) for q_hat in estimate)

        self.alive.intersection_update(reachable)
        self.save('retained_graph', status=status)

        return status

    def solve(self):
        started = perf_counter()
        self.construct()
        raw = {pair: dict(self.branches[pair]) for pair in self.ids}
        raw_record = self.record()
        status = self.prune(raw)
        retained_record = self.record()
        retained_ids = {node['id'] for node in retained_record['D'] + retained_record['O']}

        for node in raw_record['D'] + raw_record['O']:
            node['retained'] = node['id'] in retained_ids

        policy = {}
        decision_policy = {}

        for pair in self.ids:
            if pair not in self.alive:
                continue

            choices = tuple(self.branches[pair])
            decision_policy[pair] = choices

            if pair[1] in policy:
                assert policy[pair[1]] == choices, 'Observation consistency must survive merging'

            policy[pair[1]] = choices

        constructed = {}
        observations = {}

        for pair, options in raw.items():
            choices = tuple(options)

            if pair[1] in constructed:
                assert constructed[pair[1]] == choices

            constructed[pair[1]] = choices

            for choice in choices:
                key = choice.closure, choice.pattern

                if key in observations:
                    assert observations[key] == choice

                observations[key] = choice

        safe_estimates = frozenset(pair[1] for pair in self.alive if pair[1] <= self.pre.Q_e)
        result = Bipartitle_System(status, self.initial[1], self.horizon, self.window(self.initial[1]),
            policy, safe_estimates, len(raw_record['D']), len(raw_record['O']), len(raw_record['edges']),
            sum(fragment.boundary for fragment in self.fragment_cache.values()), perf_counter() - started,
            self.plant.controllable, constructed, initial_decision=self.initial,
            decision_states={pair: tuple(options) for pair, options in raw.items()},
            observation_states=observations, decision_policy=decision_policy, patterns_tested=self.tested)
        raw_record.update(schema_version=2, structure='LL-BTS', status=status, u=self.horizon,
            window=ordered(result.window), boundary_choices=result.boundary_choices,
            policy_edges=retained_record['edges'], maximal_root_patterns=[sorted(pattern) for pattern in result.maximal_patterns],
            merge=self.merge, merge_count=self.merge_count, representation='(q_hat, x_hat); example-only branch merging',
            window_semantics='One window per complete estimate',
            terminal_semantics='Safe estimates enable all events',
            patterns_tested=self.tested, generated_control_branches=self.generated_branches)

        return result, raw_record, self.history


def solve_example(pre, horizon=5, *, merge=False):
    """Only this 17-state example opts in; merging happens inside its BFS."""

    return ExampleConstruction(pre, horizon, merge=merge).solve()
