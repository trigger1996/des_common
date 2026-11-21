import unittest
from unittest.mock import patch

from des_core.automata import DFA
from des_core import certified_lookahead as ll


class LimitedReachTests(unittest.TestCase):
    def test_ur_is_endpoint_intersection_even_when_a_path_leaves_and_returns(self):
        plant = DFA(frozenset('012'), '0', frozenset(('h',)), frozenset(),
                    frozenset(), {('0', 'h'):'1', ('1', 'h'):'2', ('2', 'h'):'0'})

        self.assertEqual(ll.limited_ur(plant, frozenset('0'), frozenset(),
                                      frozenset('02')), frozenset('02'))
        self.assertEqual(ll.limited_ur(plant, frozenset('0'), frozenset(),
                                      frozenset('0')), frozenset('0'))

    def test_nx_uses_truncated_ur_not_the_full_hidden_closure(self):
        plant = DFA(frozenset('012345'), '0', frozenset(('h', 'o')),
                    frozenset(), frozenset(('o',)),
                    {('0', 'h'):'1', ('1', 'h'):'2', ('1', 'o'):'3',
                     ('2', 'o'):'4', ('3', 'h'):'5', ('3', 'o'):'5'})
        x_L = frozenset('01345')
        local = ll.limited_choice(plant, frozenset('0'), frozenset(), x_L)
        complete = ll.complete_choice(plant, frozenset('0'), frozenset())

        self.assertEqual(local.closure, frozenset('01'))
        self.assertEqual(local.successors, (('o', frozenset('3')),))
        self.assertEqual(dict(complete.successors)['o'], frozenset('34'))
        self.assertNotIn('5', dict(local.successors)['o'])

    def test_nx_clips_targets_unions_sources_and_rejects_hidden_symbols(self):
        plant = DFA(frozenset('01234'), '0', frozenset(('o', 'h')), frozenset(),
                    frozenset(('o',)), {('0', 'o'):'2', ('1', 'o'):'3', ('2', 'o'):'4'})

        self.assertEqual(ll.limited_nx(plant, frozenset('01'), 'o',
                                      frozenset('012')), frozenset('2'))
        self.assertEqual(ll.limited_nx(plant, frozenset('01'), 'o',
                                      plant.states), frozenset('23'))

        with self.assertRaises(ValueError):
            ll.limited_nx(plant, frozenset('0'), 'h', plant.states)

    def test_solver_calls_local_operators_and_does_not_certify_a_clipped_boundary(self):
        plant = DFA(frozenset('012'), '0', frozenset(('o', 'b')), frozenset(('b',)),
                    frozenset(('o', 'b')), {('0', 'o'):'1', ('1', 'o'):'1', ('1', 'b'):'2'})
        pre = ll.preprocess(plant)

        with patch.object(ll, 'limited_ur', wraps=ll.limited_ur) as ur:
            with patch.object(ll, 'limited_nx', wraps=ll.limited_nx) as nx:
                result = ll.solve_limited_lookahead(pre, horizon=0)

        self.assertGreater(ur.call_count, 0)
        self.assertGreater(nx.call_count, 0)
        self.assertEqual(result.status, 'inconclusive')
        self.assertGreater(result.boundary_choices, 0)
        complete = ll.solve_limited_lookahead(pre, horizon=1)
        self.assertEqual(complete.status, 'winning')
        ll.validate_policy(pre, complete)


if __name__ == '__main__':
    unittest.main()
