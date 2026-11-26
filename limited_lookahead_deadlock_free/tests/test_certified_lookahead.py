import itertools
import random
import unittest

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy, Limited_Lookahead_Controller
from des_core.certified_lookahead import solve_minimum_lookahead
from examples.yin_literature import build_yin_literature_examples


def dfa(transitions, controls=(), observed=(), states=None):
    states = states or set(q for q, _ in transitions) | set(transitions.values()) | {'0'}
    events = {e for _, e in transitions} | set(controls) | set(observed)

    return DFA(frozenset(states), '0', frozenset(events), frozenset(controls),
               frozenset(observed), transitions)


def independent_oracle(p):
    """All nonempty subsets + synchronous greatest fixed point, no certificates.

    Deliberately independent of production construction, UR/NX and count pruning.
    """

    subsets = lambda xs: [frozenset(c) for n in range(len(xs)+1)
                          for c in itertools.combinations(sorted(xs), n)]
    estimates, patterns = subsets(p.states)[1:], subsets(p.controllable)
    choices = {}

    for x in estimates:
        options = []

        for pattern in patterns:
            enabled = pattern | p.uncontrollable
            closure = set(x)

            while True:
                expanded = closure | {t for (q, e), t in p.transitions.items()
                                       if q in closure and e in enabled - p.observable}

                if expanded == closure:
                    break

                closure = expanded

            if any(not any(q == source and e in enabled for source, e in p.transitions)
                   for q in closure):
                continue

            successors = [frozenset(t for (q, e), t in p.transitions.items()
                                    if q in closure and e == event)
                          for event in enabled & p.observable]
            options.append((pattern, [y for y in successors if y]))

        choices[x] = options

    winning = set(estimates)

    while True:
        keep = {x for x in winning if any(all(y in winning for y in successors)
                                         for _, successors in choices[x])}

        if keep == winning:
            break

        winning = keep

    x = frozenset({p.initial})
    valid = {pattern for pattern, successors in choices[x]
             if x in winning and all(y in winning for y in successors)}

    return x in winning, {v for v in valid if not any(v < w for w in valid)}


class CertifiedTests(unittest.TestCase):
    def test_distinct_successors_and_safe_predecessor(self):
        p = dfa({('0', 'a'):'1', ('0', 'b'):'1', ('2', 'c'):'3', ('3', 'c'):'3'},
                states={'0', '1', '2', '3'})
        pre = preprocess(p)
        self.assertEqual(pre.deadlocks, {'1'})
        self.assertEqual(pre.failure, {'0'})
        self.assertEqual(pre.safe, {'2', '3'})

    def test_longest_hidden_path_requires_backtracking(self):
        p = dfa({('0', 'a'):'1', ('0', 'b'):'2', ('2', 'b'):'1', ('1', 'a'):'3',
                 ('3', 'a'):'4', ('1', 'b'):'0'}, states=set('01234'))
        pre = preprocess(p)
        self.assertEqual(pre.risk_horizon, 4)  # 0 -> 2 -> 1 -> 3 -> 4 in Q_d.

        with self.assertRaises(RuntimeError):
            preprocess(p, max_path_visits=0)

    def test_no_disabling_all_enabled_transitions(self):
        p = dfa({('0', 'a'):'0'}, ('a',))
        pre = preprocess(p)
        self.assertEqual(solve_limited_lookahead(pre).maximal_patterns, (frozenset({'a'}),))
        r = solve_limited_lookahead(pre, full=True, certificates=False)
        self.assertNotIn(frozenset(), [c.pattern for c in r.policy[r.initial]])

    def test_observable_chain_recenters_before_expanding_each_successor(self):
        p = dfa({('0', 'o'):'1', ('1', 'o'):'2', ('2', 'a'):'2', ('2', 'b'):'3'},
                ('b',), ('o', 'a', 'b'))
        pre = preprocess(p)
        self.assertEqual(pre.Q_f, frozenset())
        self.assertEqual(pre.Q_d, {'3'})
        self.assertEqual(pre.horizon, 0)
        self.assertEqual(solve_limited_lookahead(pre).status, 'winning')
        r = solve_limited_lookahead(pre, horizon=2)
        self.assertEqual(r.status, 'winning')
        validate_policy(pre, r)

    def test_online_horizon_must_be_positive_even_for_safe_initial_states(self):
        pre = preprocess(dfa({('0', 'a'):'0'}, ('a',)))
        self.assertEqual(solve_limited_lookahead(pre).horizon, 1)

        for u in (0, -1, 0.5):
            with self.assertRaises(ValueError):
                solve_limited_lookahead(pre, horizon=u)

            with self.assertRaises(ValueError):
                Limited_Lookahead_Controller(pre, horizon=u)

        with self.assertRaises(ValueError):
            solve_minimum_lookahead(pre, lower_bound=0)

    def test_deadlock_detection_bound_does_not_replace_complete_hidden_reach_check(self):
        p = dfa({('0', 'h'):'1', ('1', 'h'):'2', ('2', 'h'):'0',
                 ('0', 'b'):'3'}, ('b',), ('b',))
        pre = preprocess(p)
        self.assertFalse(pre.Q_f)
        self.assertEqual(pre.lookahead_lower_bound, 0)
        self.assertEqual(solve_limited_lookahead(pre, horizon=1).status, 'inconclusive')
        result = solve_minimum_lookahead(pre)
        self.assertEqual((result.status, result.horizon), ('winning', 2))
        validate_policy(pre, result)

    def test_empty_failure_set_still_rejects_direct_deadlock(self):
        p = dfa({('0', 'a'):'0', ('0', 'o'):'1'}, observed=('a', 'o'))
        pre = preprocess(p)
        self.assertEqual(pre.Q_f, frozenset())
        self.assertEqual(pre.Q_d, {'1'})
        self.assertEqual(pre.u_f, 0)
        result = solve_limited_lookahead(pre, horizon=1)
        self.assertEqual(result.status, 'losing')
        self.assertNotIn(result.initial, result.policy)

    def test_minimum_lookahead_checks_complete_continuation(self):
        p = dfa({('0', 'o'):'1', ('1', 'o'):'2', ('2', 'a'):'2', ('2', 'b'):'3'},
                ('b',), ('o', 'a', 'b'))
        pre = preprocess(p)
        self.assertEqual(pre.u_f, 0)
        result = solve_minimum_lookahead(pre)
        self.assertEqual((result.status, result.horizon), ('winning', 1))
        validate_policy(pre, result)
        limited = solve_minimum_lookahead(pre, max_horizon=1)
        self.assertEqual(limited.status, 'winning')

        with self.assertRaises(ValueError):
            solve_minimum_lookahead(pre, lower_bound=2, max_horizon=1)

    def test_minimum_lookahead_proved_losing_and_threshold(self):
        p = dfa({('0', 'a'):'1', ('1', 'a'):'2', ('2', 'a'):'3'})
        pre = preprocess(p)
        self.assertEqual(pre.lookahead_lower_bound, 3)
        bounded = solve_minimum_lookahead(pre)
        unrestricted = solve_minimum_lookahead(pre, lower_bound=1)
        self.assertEqual((bounded.status, bounded.horizon), ('losing', 3))
        self.assertEqual((unrestricted.status, unrestricted.horizon), ('losing', 1))

    def test_controller_minimum_horizon_rebuilds_after_observation(self):
        p = dfa({('0', 'o'):'1', ('1', 'a'):'1', ('1', 'b'):'2'}, ('b',), ('o', 'a', 'b'))
        controller = Limited_Lookahead_Controller(preprocess(p), minimum_horizon=True)
        proof, fresh, fallback = controller.solve()
        self.assertEqual((proof.status, controller.horizon, fallback), ('winning', 1, False))
        pattern = proof.maximal_patterns[-1]
        controller.observe(pattern, 'o')
        self.assertEqual(controller.estimate, {'1'})
        proof, fresh, fallback = controller.solve()
        self.assertEqual(proof.initial, {'1'})
        self.assertEqual(proof.window, {'1', '2'})
        validate_policy(controller.pre, proof)

    def test_complete_belief_not_selected_actual_successor(self):
        p = dfa({('0', 'h'):'1', ('0', 'o'):'2', ('1', 'o'):'3',
                 ('2', 'a'):'2', ('3', 'b'):'3'}, ('a', 'b'), ('o', 'a', 'b'))
        pre = preprocess(p)
        r = solve_limited_lookahead(pre, full=True, certificates=False)
        first = r.policy[r.initial]
        self.assertTrue(all(c.successors == (('o', frozenset({'2', '3'})),) for c in first))
        validate_policy(pre, r)

    def test_controller_preserves_proved_continuation_across_windows(self):
        from examples.non_deadlock import build_small_cycle_example

        controller = Limited_Lookahead_Controller(preprocess(build_small_cycle_example().dfa), 2)
        fallbacks = 0

        for k in range(15):
            proof, fresh, fallback = controller.solve()
            self.assertEqual(proof.status, 'winning')
            validate_policy(controller.pre, proof)
            fallbacks += fallback
            choices = proof.policy.get(controller.estimate, ())
            pattern = proof.maximal_patterns[-1]
            choice = next(c for c in choices if c.pattern == pattern)
            event, _ = choice.successors[k%len(choice.successors)]
            controller.observe(pattern, event)

        self.assertEqual(fallbacks, 0)

    def test_paper_models_and_transcription(self):
        es = build_yin_literature_examples(amended=False)
        self.assertEqual(len(es), 61)
        self.assertEqual([(len(e.dfa.states), len(e.dfa.transitions)) for e in es[:6]],
                         [(7, 11), (5, 6), (2, 2), (6, 10), (8, 13), (8, 11)])

        for e in es:
            pre = preprocess(e.dfa)
            raw = solve_limited_lookahead(pre, full=True, certificates=False)
            cert = solve_limited_lookahead(pre, full=True)
            self.assertEqual((raw.status, raw.maximal_patterns), (cert.status, cert.maximal_patterns), e.name)
            validate_policy(pre, raw)
            validate_policy(pre, cert)

    def test_independent_random_oracle_and_all_horizons(self):
        rng = random.Random(20261120)

        for i in range(90):
            states = [str(k) for k in range(rng.randint(2, 5))]
            events = ['a', 'b', 'o']
            transitions = {(q, e):rng.choice(states) for q in states for e in events
                           if rng.random() < .48}
            p = dfa(transitions, [e for e in events if rng.random()<.5],
                    [e for e in events if rng.random()<.5], set(states))
            pre = preprocess(p)
            expected, maximal = independent_oracle(p)

            for certs in (False, True):
                r = solve_limited_lookahead(pre, full=True, certificates=certs)
                self.assertEqual(r.status == 'winning', expected, (i, certs))
                self.assertEqual(set(r.maximal_patterns), maximal, (i, certs))
                validate_policy(pre, r)

            sweep = []

            for u in range(1, max(2, len(states))):
                r = solve_limited_lookahead(pre, horizon=u)
                sweep.append(r)

                if r.status == 'winning':
                    self.assertTrue(expected, i)
                    validate_policy(pre, r)
                elif r.status == 'losing':
                    self.assertFalse(expected, i)

            minimum = solve_minimum_lookahead(pre, lower_bound=1)
            first = next(r for r in sweep if r.status != 'inconclusive')
            self.assertEqual((minimum.horizon, minimum.status, minimum.maximal_patterns),
                             (first.horizon, first.status, first.maximal_patterns), i)


if __name__ == '__main__':
    unittest.main()
