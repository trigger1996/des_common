import unittest

from examples.large_scale.early_stop_products import analyze, full_counts
from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_minimum_lookahead, validate_policy
from des_core.offline_bts import construct_offline_bts


class EarlyStopProductTests(unittest.TestCase):
    def test_product_subsets_and_full_counts_match_explicit_analysis(self):
        for kind in ('E', 'H'):
            with self.subTest(kind=kind):
                pre = analyze(kind, 6, 2)
                p = pre.plant
                states = frozenset(p.states)
                transitions = {(q, e): t for q in states for e, t in p.enabled(q)}
                explicit = DFA(states, p.initial, p.events, p.controllable, p.observable, transitions)
                exact = preprocess(explicit)
                self.assertEqual(exact.Q_d, pre.Q_d)
                self.assertEqual(exact.Q_f, pre.Q_f)
                self.assertEqual(exact.Q_e, frozenset(pre.Q_e))
                self.assertEqual(exact.Q_o_tilde, frozenset(pre.Q_o_tilde))
                self.assertEqual((exact.u, exact.u_f), (pre.u, pre.u_f))
                full = construct_offline_bts(explicit)
                predicted = full_counts(6, 2)
                self.assertEqual((full.decision_count, full.observation_count),
                                 (predicted['D'], predicted['O']))

    def test_E_can_stop_globally_after_first_observation(self):
        pre = analyze('E', 10, 3)
        self.assertFalse(frozenset({pre.plant.initial}) <= pre.Q_e)
        self.assertTrue(pre.Q_d)
        result = solve_minimum_lookahead(pre)
        self.assertEqual((result.status, result.horizon), ('winning', 1))
        self.assertEqual((result.decision_count, result.observation_count), (703, 3944))
        self.assertGreater(validate_policy(pre, result)['estimates'], 0)

    def test_H_requires_more_global_lookahead_and_retains_a_live_policy(self):
        pre = analyze('H', 10, 3)
        result = solve_minimum_lookahead(pre)
        self.assertEqual((result.status, result.horizon), ('winning', 1))
        self.assertTrue(result.safe_terminals)
        self.assertGreater(validate_policy(pre, result)['choices'], 0)


if __name__ == '__main__':
    unittest.main()
