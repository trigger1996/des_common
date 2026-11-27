import unittest
import json

from des_core.asynchronous_product import ImplicitProductDFA
from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_minimum_lookahead, validate_policy
from des_core.offline_bts import construct_offline_bts
from examples.large_scale.nonzero_lookahead_cases import CASES, INPUTS, base_model, model_record, reachable_count


class NonzeroLookaheadCasesTest(unittest.TestCase):
    def test_durable_inputs_match_measured_models_and_product_parameters(self):
        for case, (kind, n, copies, hidden_steps) in CASES.items():
            recipe = json.loads((INPUTS / case / 'model.json').read_text(encoding='utf-8'))
            self.assertEqual(recipe['global_states'], n ** copies)
            self.assertEqual(recipe['copies'], copies)
            self.assertEqual(recipe['expected_bar_u'], copies * hidden_steps)
            source = INPUTS / case / recipe['component_file']
            self.assertTrue(source.is_file())

            if kind != 'C':
                self.assertEqual(json.loads(source.read_text(encoding='utf-8')),
                                 model_record(base_model(kind, n, hidden_steps)))

    def test_revised_products_have_exact_positive_thresholds_and_safe_policies(self):
        for kind, hidden_steps in [('E', 2), ('H', 1), ('P', 2)]:
            for copies in (1, 2):
                with self.subTest(kind=kind, copies=copies):
                    base = base_model(kind, 6, hidden_steps)
                    self.assertEqual(base.observable, frozenset({'a', 'b'}))
                    self.assertEqual(base.controllable, frozenset({'b'}))
                    product = ImplicitProductDFA(base, copies)
                    states = frozenset(product.states)
                    plant = DFA(states, product.initial, product.events, product.controllable,
                                product.observable, {(q, e): t for q in states for e, t in product.enabled(q)})
                    pre = preprocess(plant)
                    self.assertEqual(pre.lookahead_lower_bound, hidden_steps * copies)
                    self.assertTrue(pre.Q_d)
                    self.assertTrue(pre.Q_f)
                    self.assertTrue(pre.Q_e)
                    self.assertEqual(reachable_count(plant), len(states))
                    full = construct_offline_bts(plant)
                    ll = solve_minimum_lookahead(pre)
                    self.assertEqual(full.status, 'winning')
                    self.assertEqual(ll.status, full.status)
                    self.assertEqual(set(ll.maximal_patterns), set(full.maximal_patterns))
                    self.assertGreater(validate_policy(pre, ll)['choices'], 0)

    def test_zero_bound_control_is_unchanged_and_solvable(self):
        pre = preprocess(base_model('E', 10, 0))
        self.assertEqual(pre.lookahead_lower_bound, 0)
        ll = solve_minimum_lookahead(pre)
        self.assertEqual(ll.horizon, 1)
        self.assertEqual(ll.status, 'winning')
        validate_policy(pre, ll)

    def test_explicit_chain_has_positive_threshold_and_safe_continuation(self):
        pre = preprocess(base_model('C', 140, 2))
        self.assertEqual(pre.lookahead_lower_bound, 2)
        ll = solve_minimum_lookahead(pre)
        self.assertEqual(ll.status, 'winning')
        self.assertEqual(ll.status, construct_offline_bts(pre.plant).status)
        validate_policy(pre, ll)


if __name__ == '__main__':
    unittest.main()
