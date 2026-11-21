"""Differential checks against the full explicit control-pattern family."""

import random
import unittest

from des_core.automata import DFA
from des_core.asynchronous_product import ImplicitProductDFA
from des_core.implicit_product import benchmark_case1_product
from des_core.ll_bts import construct_ll_bts
from des_core.ll_bts_synthesis import synthesize_ll_bts_controls
from examples.non_deadlock import build_small_cycle_example


class ControlReductionTests(unittest.TestCase):
    def compare(self, plant, root, horizon):
        explicit = construct_ll_bts(plant, root, horizon, False)
        expected = synthesize_ll_bts_controls(plant, root, explicit)

        for mode in ('reduced', 'factored'):
            actual = construct_ll_bts(plant, root, horizon, False, pattern_mode=mode)

            if mode == 'reduced':
                self.assertEqual(actual.decision_states, explicit.decision_states)
                self.assertEqual(actual.searched_states, explicit.searched_states)
                self.assertEqual(actual.maximal_good_patterns, explicit.maximal_good_patterns)
            else:
                # Factored construction also applies known Algorithm-2 losses
                # early, so its search is a subset of the unpruned structure.
                self.assertLessEqual(actual.decision_states, explicit.decision_states)
                self.assertLessEqual(actual.searched_states, explicit.searched_states)

            self.assertEqual(synthesize_ll_bts_controls(plant, root, actual), expected)

    def test_random_plants_and_horizon_boundaries(self):
        rng = random.Random(20260911)
        states = tuple(str(i) for i in range(5))
        events = tuple('abcde')

        for case in range(300):
            plant = DFA(frozenset(states), '0', frozenset(events),
                        frozenset(e for e in events if rng.random() < .7),
                        frozenset(e for e in events if rng.random() < .5),
                        {(q, e): rng.choice(states) for q in states for e in events
                         if rng.random() < .5})

            for horizon in range(4):
                with self.subTest(case=case, horizon=horizon):
                    self.compare(plant, plant.initial, horizon)

    def test_product_roots(self):
        component = build_small_cycle_example().dfa

        for copies in (1, 2, 3):
            product = ImplicitProductDFA(component, copies)

            for local in sorted(component.states):
                root = (local,) + product.initial[1:]

                for horizon in range(4):
                    with self.subTest(copies=copies, root=root, horizon=horizon):
                        self.compare(product, root, horizon)

    def test_factored_can_disable_one_observable_and_retain_another(self):
        plant = DFA(frozenset(('0', '1')), '0', frozenset(('a', 'b')),
                    frozenset(('a', 'b')), frozenset(('a', 'b')),
                    {('0', 'a'): '0', ('0', 'b'): '1'})
        self.compare(plant, '0', 2)
        result = construct_ll_bts(plant, '0', 2, False, pattern_mode='factored')
        self.assertEqual(synthesize_ll_bts_controls(plant, '0', result).maximal_patterns,
                         (frozenset(('a',)),))

    def test_cache_does_not_change_online_trace(self):
        component = build_small_cycle_example().dfa
        a = benchmark_case1_product(component, 2, 8, 2, cache_size=0)
        b = benchmark_case1_product(component, 2, 8, 2, cache_size=4)
        fields = ('current', 'local_state_count', 'local_edge_count', 'next_state',
                  'selected_event', 'cumulative_state_count')
        self.assertEqual([tuple(getattr(s, f) for f in fields) for s in a.stats],
                         [tuple(getattr(s, f) for f in fields) for s in b.stats])
        self.assertEqual(a.synthesis_calls, a.iterations)
        self.assertEqual(a.cache_hits, 0)

    def test_unique_represented_edges(self):
        plant = build_small_cycle_example().dfa

        for mode in ('explicit', 'reduced', 'factored'):
            result = construct_ll_bts(plant, plant.initial, 3, True, pattern_mode=mode)
            self.assertEqual(result.edge_count, len(result.edges))

    def test_transition_index_cannot_become_stale(self):
        transitions = {('0', 'a'): '0'}
        plant = DFA(frozenset(('0',)), '0', frozenset(('a',)),
                    frozenset(), frozenset(), transitions)
        self.assertEqual(plant.enabled('0'), (('a', '0'),))
        transitions.clear()
        self.assertEqual(plant.enabled('0'), (('a', '0'),))

        with self.assertRaises(TypeError):
            plant.transitions[('0', 'a')] = '1'


if __name__ == '__main__':
    unittest.main()
