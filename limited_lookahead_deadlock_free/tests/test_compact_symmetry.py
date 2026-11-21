import itertools
import random
import unittest

from des_core.automata import DFA
from des_core.asynchronous_product import ImplicitProductDFA, AsynchronousProductDFA
from des_core.compact_ll_bts import CompactGraph, construct_compact
from des_core.limited_lookahead import post_leq
from des_core.ll_bts import construct_ll_bts
from des_core.ll_bts_synthesis import synthesize_ll_bts_controls
from examples.non_deadlock import build_small_cycle_example


class CompactSymmetryTests(unittest.TestCase):
    def compare(self, plant, root, horizon):
        window = post_leq(plant, frozenset({root}), horizon)
        plain = construct_compact(plant, root, window, None, use_symmetry=False)
        folded = construct_compact(plant, root, window, None)

        for field in ('decision_states', 'observation_states'):
            a, b = getattr(plain, field), getattr(folded, field)
            self.assertEqual(len(a), len(b))
            self.assertEqual(set(a), set(b))

        for field in ('edge_count', 'searched_states', 'decision_estimate_states',
                      'observation_estimate_states', 'maximal_good_patterns'):
            self.assertEqual(getattr(plain, field), getattr(folded, field), field)

        self.assertEqual(set(plain.control_choices), set(folded.control_choices))

        for estimate, choices in plain.control_choices.items():
            self.assertEqual(set(choices), set(folded.control_choices[estimate]))

        self.assertEqual(synthesize_ll_bts_controls(plant, root, plain),
                         synthesize_ll_bts_controls(plant, root, folded))

    def test_all_two_copy_roots(self):
        component = build_small_cycle_example().dfa
        plant = ImplicitProductDFA(component, 2)

        for root in itertools.product(sorted(component.states), repeat=2):
            for horizon in range(4):
                with self.subTest(root=root, horizon=horizon):
                    self.compare(plant, root, horizon)

    def test_three_copy_mixed_roots(self):
        component = build_small_cycle_example().dfa
        plant = ImplicitProductDFA(component, 3)
        roots = [('q_1', 'q_1', 'q_0'), ('q_3', 'q_0', 'q_3'),
                 ('q_4', 'q_1', 'q_4'), ('q_5', 'q_5', 'q_0'), plant.initial]

        for root in roots:
            self.compare(plant, root, 3)

    def test_random_repeated_components(self):
        rng = random.Random(1219)

        for case in range(30):
            states = ('0', '1', '2')
            events = ('a', 'b')
            component = DFA(frozenset(states), '0', frozenset(events),
                            frozenset(e for e in events if rng.random() < .6),
                            frozenset(e for e in events if rng.random() < .6),
                            {(q, e): rng.choice(states) for q in states for e in events
                             if rng.random() < .7})
            plant = ImplicitProductDFA(component, 3)
            root = tuple(rng.choice(states) for _ in range(3))

            with self.subTest(case=case):
                self.compare(plant, root, 2)

    def test_histogram_ties_are_not_assumed_equivalent(self):
        component = DFA(frozenset(('0', '1')), '0', frozenset(('a',)),
                        frozenset(('a',)), frozenset(),
                        {('0', 'a'): '1', ('1', 'a'): '0'})
        plant = ImplicitProductDFA(component, 6)
        window = post_leq(plant, frozenset({plant.initial}), 3)
        graph = CompactGraph(plant, window, plant.initial)

        def edge_estimate(edges):
            return graph.encode(tuple(tuple('1' if i in edge else '0' for i in range(6))
                                      for edge in edges))

        cycle = edge_estimate([(i, (i + 1) % 6) for i in range(6)])
        triangles = edge_estimate([(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])
        # Both have six rows and two '1' entries in every column, but are not
        # related by a coordinate permutation (one cycle versus two cycles).
        self.assertNotEqual(graph.canonical(cycle)[0], graph.canonical(triangles)[0])

        for mask in (cycle, triangles):
            canonical, perm, size = graph.canonical(mask)
            self.assertEqual(graph.symmetry.transform(mask, perm), canonical)
            orbit = list(graph.orbit(mask))
            self.assertEqual(size, len(orbit))

            for other, _ in orbit:
                self.assertEqual(graph.canonical(other)[0], canonical)

    def test_different_components_are_not_permuted(self):
        a = build_small_cycle_example().dfa
        b = DFA(a.states, a.initial, a.events, a.controllable, frozenset(), a.transitions)
        plant = AsynchronousProductDFA((a, b))
        result = construct_ll_bts(plant, plant.initial, 2, False, pattern_mode='factored')
        self.assertIsNone(result._compact_graph.symmetry)


if __name__ == '__main__':
    unittest.main()
