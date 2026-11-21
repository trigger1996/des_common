import unittest
from des_core.automata import DFA
from des_core.ll_bts import construct_ll_bts
from des_core.ll_bts_synthesis import synthesize_ll_bts_controls
from des_core.implicit_product import benchmark_case1_product


def plant(transitions, observable=(), controllable=(), states=('q_0',)):
    return DFA(frozenset(states) | frozenset(q for (q, _e) in transitions)
               | frozenset(transitions.values()), 'q_0',
               frozenset(e for _q, e in transitions), frozenset(controllable),
               frozenset(observable), transitions)


def solve(p, horizon=5):
    return synthesize_ll_bts_controls(p, p.initial, construct_ll_bts(p, p.initial, horizon, False))


class Algorithm2Tests(unittest.TestCase):
    def test_deadlock_returns_normally_even_with_full_iterations_flag(self):
        r = benchmark_case1_product(plant({}), 1, 20, 2, require_full_iterations=True)
        self.assertEqual((r.iterations, r.stop_reason), (1, 'empty_synthesis'))
        self.assertIsNone(r.stats[-1].next_state)

    def test_nonempty_without_forward_successor_returns(self):
        p = plant({('q_0', 'u'): 'q_0'})
        self.assertFalse(solve(p).empty)
        r = benchmark_case1_product(p, 1, 20, 2)
        self.assertEqual((r.iterations, r.stop_reason), (1, 'no_forward_successor'))

    def test_recursive_environment_loss_reaches_initial(self):
        p = plant({('q_0', 'o'): 'q_1', ('q_1', 'o'): 'q_2'}, ('o',))
        self.assertTrue(solve(p).empty)

    def test_safe_control_survives_bad_alternative(self):
        p = plant({('q_0', 'a'): 'q_0', ('q_0', 'b'): 'q_1'}, ('a', 'b'), ('b',))
        r = solve(p)
        self.assertFalse(r.empty)
        self.assertEqual(r.maximal_patterns, (frozenset(),))
        self.assertEqual(r.forward_successors, ((frozenset(), 'a', 'q_0'),))

    def test_one_bad_environment_outcome_invalidates_choice(self):
        p = plant({('q_0', 'a'): 'q_0', ('q_0', 'b'): 'q_1'}, ('a', 'b'))
        self.assertTrue(solve(p).empty)

    def test_pending_not_automatically_empty(self):
        p = plant({('q_0', 'u'): 'q_1', ('q_1', 'u'): 'q_1'})
        self.assertFalse(solve(p, 0).empty)
        self.assertEqual(solve(p, 0).forward_successors, ())

    def test_horizon_boundary_observable_successor_is_not_inconsistent(self):
        p = plant({('q_0', 'o'): 'q_1', ('q_1', 'o'): 'q_1'}, ('o',))
        self.assertFalse(solve(p, 0).empty)

    def test_online_advance_uses_observable_successor_after_unobservable_reach(self):
        p = plant({('q_0', 'u'): 'q_1', ('q_1', 'o'): 'q_0'}, ('o',))
        r = benchmark_case1_product(p, 1, 4, 2)
        self.assertEqual((r.iterations, r.stop_reason), (4, 'iteration_limit'))
        self.assertTrue(all(s.selected_event == 'o_0' and s.next_state == ('q_0',) for s in r.stats))


class LLBTSOptimizationInvariantTests(unittest.TestCase):
    def test_reported_edge_count_matches_unique_stored_edges(self):
        p = plant({('q_0', 'a'): 'q_0', ('q_0', 'b'): 'q_1'}, ('a', 'b'), ('b',))
        r = construct_ll_bts(p, p.initial, 3, True)
        self.assertEqual(r.edge_count, len(r.edges))

    def test_uncontrollable_events_are_implicitly_enabled_in_compact_patterns(self):
        p = plant({('q_0', 'u'): 'q_0'}, (), (), states=('q_0',))
        r = solve(p)
        self.assertFalse(r.empty)


if __name__ == '__main__':
    unittest.main()
