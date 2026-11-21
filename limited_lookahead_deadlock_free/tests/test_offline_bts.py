import unittest

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess,solve_certified,validate_policy
from des_core.offline_bts import construct_offline_bts,BTSBudgetExceeded


class OfflineBTSTests(unittest.TestCase):
    def test_large_indexed_bts_matches_general_traditional_solver(self):
        from large_online_offline import known_input,indexed_offline_bts,indexed_online
        for n in (3,7,15):
            for terminal in (False,True):
                successor=known_input(n,terminal)
                plant=DFA(frozenset(map(str,range(n))),'0',frozenset(('o',)),frozenset(),
                    frozenset(('o',)),{(str(q),'o'):str(t) for q,t in enumerate(successor) if t>=0})
                general=construct_offline_bts(plant)
                indexed=indexed_offline_bts(successor);online=indexed_online(successor)
                pre=preprocess(plant)
                self.assertEqual((indexed['status'],indexed['D'],indexed['O'],indexed['edges']),
                                 (general.status,general.decision_count,general.observation_count,general.edge_count))
                self.assertEqual((online['Qd'],online['Qf'],online['Qe']),
                                 (len(pre.deadlocks),len(pre.failure),len(pre.safe)))
                self.assertEqual(online['status'],general.status)

    def test_exact_product_certificates_and_lazy_state_space(self):
        from large_online_offline import verify_product_certificates
        from examples.non_deadlock import build_small_cycle_example
        from des_core.asynchronous_product import ImplicitProductDFA
        verify_product_certificates()
        product=ImplicitProductDFA(build_small_cycle_example().dfa,8)
        self.assertEqual(len(product.states),6**8)
        self.assertIn(product.initial,product.states)
        self.assertNotIn(('invalid',)*8,product.states)
        small=ImplicitProductDFA(build_small_cycle_example().dfa,1)
        self.assertEqual(small.states-frozenset(),frozenset(small.states))

    def test_constructs_unsafe_branches_before_pruning(self):
        plant=DFA(frozenset('012'),'0',frozenset(('o','b')),frozenset(('b',)),
            frozenset(('o','b')),{('0','o'):'1',('1','o'):'1',('1','b'):'2'})
        result=construct_offline_bts(plant)
        self.assertIn(frozenset(('2',)),result.constructed_choices)
        self.assertEqual(len(result.constructed_choices[frozenset(('2',))]),2)
        self.assertNotIn(frozenset(('2',)),result.policy)
        self.assertEqual(result.safe_terminals,frozenset())
        self.assertIsNone(result.horizon)
        validate_policy(preprocess(plant),result)

    def test_hidden_cycle_with_no_observation_is_not_a_deadlock(self):
        plant=DFA(frozenset(('0',)),'0',frozenset(('h',)),frozenset(('h',)),
                  frozenset(),{('0','h'):'0'})
        result=construct_offline_bts(plant)
        self.assertEqual(result.status,'winning')
        self.assertEqual(result.maximal_patterns,(frozenset(('h',)),))

    def test_budget_truncation_never_returns_a_synthesis_conclusion(self):
        plant=DFA(frozenset(('0',)),'0',frozenset(('a','b')),frozenset(('a','b')),
            frozenset(('a','b')),{('0','a'):'0',('0','b'):'0'})
        with self.assertRaises(BTSBudgetExceeded) as caught:
            construct_offline_bts(plant,max_choices=1)
        self.assertFalse(caught.exception.metrics['complete'])
        with self.assertRaises(BTSBudgetExceeded):
            solve_certified(preprocess(plant),certificates=False,full=True,max_choices=1)


if __name__=='__main__':unittest.main()
