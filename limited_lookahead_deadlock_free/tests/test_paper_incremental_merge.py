from dataclasses import replace
import unittest

from des_core.certified_lookahead import Choice, preprocess, solve_limited_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from examples.paper_fig1_r1.incremental_merge import Fragment, merge_at_insertion, solve_example
from paper_example_models import paper_small_figure_r1


class PaperIncrementalMergeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pre = preprocess(paper_small_figure_r1().dfa)

    def test_default_off_preserves_the_original_graph_and_controller(self):
        actual, record, steps = solve_example(self.pre)
        expected = solve_limited_lookahead(self.pre, horizon=5)
        self.assertEqual(actual.decision_states, expected.decision_states)
        self.assertEqual(actual.observation_states, expected.observation_states)
        self.assertEqual(actual.policy, expected.policy)
        self.assertEqual(actual.edge_count, expected.edge_count)
        self.assertFalse(record['merge'])
        self.assertFalse(any(step['operation'] == 'merge_pattern' for step in steps))

    def test_merging_preserves_all_decision_pairs_and_the_selected_closed_loop(self):
        original, _, _ = solve_example(self.pre, merge=False)
        merged, record, _ = solve_example(self.pre, merge=True)
        self.assertEqual(set(original.decision_states), set(merged.decision_states))
        self.assertEqual(merged.decision_count, 8)
        self.assertEqual(merged.observation_count, 12)
        self.assertEqual(len(merged.decision_policy), 5)
        self.assertEqual(sum(row['retained'] for row in record['O']), 4)
        self.assertEqual(original.maximal_patterns, merged.maximal_patterns)
        self.assertEqual(build_closed_loop(self.pre, original), build_closed_loop(self.pre, merged))
        validate_policy(self.pre, merged)

    def test_every_merge_occurs_before_the_next_construction_pattern(self):
        _, _, steps = solve_example(self.pre, merge=True)
        completed = next(step['step'] for step in steps if step['operation'] == 'construction_complete')
        merges = [step for step in steps if step['operation'] == 'merge_pattern']
        self.assertTrue(merges)

        for step in merges:
            self.assertLess(step['step'], completed)
            smaller = set(step['details']['smaller_gamma_c'])
            larger = set(step['details']['larger_gamma_c'])
            self.assertLess(smaller, larger)
            previous = steps[step['step'] - 1]
            self.assertIn(previous['operation'], ('construct_pattern', 'merge_pattern'))
            self.assertEqual(previous['details']['decision'], step['details']['decision'])
            self.assertFalse(any(edge[0] == step['details']['decision'] and edge[1] == step['details']['discarded']
                                 for edge in step['edges']))

    def test_observable_event_labels_are_part_of_the_merge_condition(self):
        small = Choice(frozenset({'a'}), frozenset({'q'}), (('o1', frozenset({'r'})),))
        large = Choice(frozenset({'a', 'b'}), frozenset({'q'}), (('o2', frozenset({'r'})),))
        first = Fragment(small, small, True, True)
        second = Fragment(large, large, True, True)
        active = {small: first, large: second}
        self.assertFalse(merge_at_insertion(active, second))
        self.assertEqual(len(active), 2)

    def test_incomparable_patterns_and_different_liveness_do_not_merge(self):
        a = Choice(frozenset({'a'}), frozenset({'q'}), ())
        b = Choice(frozenset({'b'}), frozenset({'q'}), ())
        first = Fragment(a, a, True, True)
        second = Fragment(b, b, True, True)
        active = {a: first, b: second}
        self.assertFalse(merge_at_insertion(active, second))
        larger = Choice(frozenset({'a', 'b'}), frozenset({'q'}), ())
        blocked = Fragment(larger, larger, False, True)
        active[larger] = blocked
        self.assertFalse(merge_at_insertion(active, blocked))

    def test_insufficient_horizon_stays_inconclusive(self):
        merged, _, _ = solve_example(self.pre, horizon=1, merge=True)
        self.assertEqual(merged.status, 'inconclusive')


if __name__ == '__main__':
    unittest.main()
