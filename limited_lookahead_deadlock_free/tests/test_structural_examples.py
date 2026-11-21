import unittest
import networkx as nx

from examples.structural import build_structural_examples
from des_core.certified_lookahead import preprocess,solve_offline,solve_certified,validate_policy
from des_core.closed_loop import build_closed_loop


class StructuralExampleTests(unittest.TestCase):
    def test_long_chain_has_a_real_terminal_and_is_losing(self):
        plant=build_structural_examples()[0].dfa
        self.assertEqual(len(plant.states),16)
        self.assertEqual(len(plant.transitions),15)
        self.assertEqual(plant.enabled('q15'),())
        self.assertTrue(all(len(plant.enabled('q%d'%i))==1 for i in range(15)))
        self.assertEqual(solve_offline(plant).status,'losing')

    def test_cycle_with_two_terminal_tails_can_disable_both_exits(self):
        plant=build_structural_examples()[1].dfa
        pre=preprocess(plant)
        self.assertEqual(pre.deadlocks,frozenset(('q11','q14')))
        result=solve_certified(pre,full=True)
        self.assertEqual(result.status,'winning');validate_policy(pre,result)
        graph=build_closed_loop(pre,result)
        self.assertFalse({e['event'] for e in graph['edges']} & {'x','y'})
        physical=nx.DiGraph()
        physical.add_edges_from((q,t) for (q,e),t in plant.transitions.items())
        self.assertEqual([len(c) for c in nx.simple_cycles(physical)],[4])

    def test_nested_cycles_share_an_outer_cycle_state(self):
        plant=build_structural_examples()[2].dfa
        physical=nx.DiGraph()
        physical.add_edges_from((q,t) for (q,e),t in plant.transitions.items())
        cycles=list(nx.simple_cycles(physical))
        self.assertEqual(sorted(map(len,cycles)),[3,4])
        self.assertEqual(set(cycles[0]) & set(cycles[1]),{'q6'})
        pre=preprocess(plant)
        self.assertEqual(pre.safe,plant.states)
        result=solve_certified(pre,full=True)
        self.assertEqual(result.status,'winning');validate_policy(pre,result)


if __name__=='__main__':unittest.main()
