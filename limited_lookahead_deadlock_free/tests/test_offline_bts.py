import unittest

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.offline_bts import (construct_offline_bts, BTSBudgetExceeded,
    traditional_ur, traditional_nx, traditional_ur_nx)


class OfflineBTSTests(unittest.TestCase):
    def test_ur_takes_many_hidden_steps_but_nx_takes_one_observable_event(self):
        edges = {('0', 'a'):'1', ('1', 'b'):'2', ('2', 'a'):'1',
               ('2', 'o1'):'3', ('1', 'o2'):'4', ('3', 'h'):'5', ('3', 'o2'):'6'}
        plant = DFA(frozenset('0123456'), '0', frozenset(('a', 'b', 'h', 'o1', 'o2')),
            frozenset(('b', 'o2')), frozenset(('o1', 'o2')), edges)
        pattern = frozenset(('b', 'o2'))
        closure = traditional_ur(plant, iter(('0',)), pattern)
        self.assertEqual(closure, frozenset('012'))
        self.assertEqual(traditional_nx(plant, closure, 'o1'), frozenset('3'))
        self.assertEqual(traditional_nx(plant, closure, 'o2'), frozenset('4'))
        # Neither hidden h after o1 nor a subsequent o2 belongs to this NX.
        self.assertNotIn('5', traditional_nx(plant, closure, 'o1'))
        self.assertNotIn('6', traditional_nx(plant, closure, 'o1'))
        choice = traditional_ur_nx(plant, frozenset('0'), pattern)
        self.assertEqual(choice.closure, closure)
        self.assertEqual(dict(choice.successors), {'o1':frozenset('3'), 'o2':frozenset('4')})
        # Disabling b shortens UR; disabling o2 removes only that NX entry.
        blocked = traditional_ur_nx(plant, frozenset('0'), frozenset())
        self.assertEqual(blocked.closure, frozenset('01'))
        self.assertEqual(blocked.successors, ())

    def test_nx_unions_same_symbol_targets_without_computing_ur(self):
        plant = DFA(frozenset('0123'), '0', frozenset(('o', 'h')), frozenset(),
            frozenset(('o',)), {('0', 'o'):'2', ('1', 'o'):'3', ('0', 'h'):'1'})
        self.assertEqual(traditional_nx(plant, frozenset('0'), 'o'), frozenset('2'))
        self.assertEqual(traditional_nx(plant, frozenset('01'), 'o'), frozenset('23'))

        with self.assertRaises(ValueError):traditional_nx(plant, frozenset('0'), 'h')

    def test_large_indexed_bts_matches_general_traditional_solver(self):
        from examples.large_scale.large_online_offline import known_input, indexed_offline_bts, indexed_online

        for n in (3, 7, 15):
            for terminal in (False, True):
                successor = known_input(n, terminal)
                plant = DFA(frozenset(map(str, range(n))), '0', frozenset(('o',)), frozenset(),
                    frozenset(('o',)), {(str(q), 'o'):str(t) for q, t in enumerate(successor) if t >= 0})
                general = construct_offline_bts(plant)
                indexed = indexed_offline_bts(successor);online = indexed_online(successor)
                pre = preprocess(plant)
                self.assertEqual((indexed['status'], indexed['D'], indexed['O'], indexed['edges']),
                                 (general.status, general.decision_count, general.observation_count, general.edge_count))
                self.assertEqual((online['Qd'], online['Qf'], online['Qe']),
                                 (len(pre.deadlocks), len(pre.failure), len(pre.safe)))
                self.assertEqual(online['status'], general.status)

    def test_exact_product_certificates_and_lazy_state_space(self):
        from examples.large_scale.large_online_offline import verify_product_certificates
        from examples.non_deadlock import build_small_cycle_example
        from des_core.asynchronous_product import ImplicitProductDFA

        verify_product_certificates()
        product = ImplicitProductDFA(build_small_cycle_example().dfa, 8)
        self.assertEqual(len(product.states), 6**8)
        self.assertIn(product.initial, product.states)
        self.assertNotIn(('invalid',)*8, product.states)
        small = ImplicitProductDFA(build_small_cycle_example().dfa, 1)
        self.assertEqual(small.states-frozenset(), frozenset(small.states))

    def test_constructs_unsafe_branches_before_pruning(self):
        plant = DFA(frozenset('012'), '0', frozenset(('o', 'b')), frozenset(('b',)),
            frozenset(('o', 'b')), {('0', 'o'):'1', ('1', 'o'):'1', ('1', 'b'):'2'})
        result = construct_offline_bts(plant)
        self.assertIn(frozenset(('2',)), result.constructed_choices)
        self.assertEqual(len(result.constructed_choices[frozenset(('2',))]), 2)
        self.assertNotIn(frozenset(('2',)), result.policy)
        self.assertEqual(result.safe_terminals, frozenset())
        self.assertIsNone(result.horizon)
        validate_policy(preprocess(plant), result)

    def test_hidden_cycle_with_no_observation_is_not_a_deadlock(self):
        plant = DFA(frozenset(('0',)), '0', frozenset(('h',)), frozenset(('h',)),
                  frozenset(), {('0', 'h'):'0'})
        result = construct_offline_bts(plant)
        self.assertEqual(result.status, 'winning')
        self.assertEqual(result.maximal_patterns, (frozenset(('h',)),))

    def test_budget_truncation_never_returns_a_synthesis_conclusion(self):
        plant = DFA(frozenset(('0',)), '0', frozenset(('a', 'b')), frozenset(('a', 'b')),
            frozenset(('a', 'b')), {('0', 'a'):'0', ('0', 'b'):'0'})

        with self.assertRaises(BTSBudgetExceeded) as caught:
            construct_offline_bts(plant, max_choices=1)

        self.assertFalse(caught.exception.metrics['complete'])

        with self.assertRaises(BTSBudgetExceeded):
            solve_limited_lookahead(preprocess(plant), certificates=False, full=True, max_choices=1)


if __name__ == '__main__':unittest.main()
