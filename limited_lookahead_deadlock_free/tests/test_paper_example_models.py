import unittest

from examples.non_deadlock import build_small_cycle_example, build_nested_cycle_deadlock_example
from paper_example_models import paper_small_figure, archived_component_figure
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, solve_offline, validate_policy, complete_choice


class PaperExampleTests(unittest.TestCase):
    def test_paper_variants_do_not_overwrite_current_models(self):
        small = paper_small_figure().dfa;old = archived_component_figure().dfa
        self.assertEqual(small.transitions['q_10', 'o2'], 'q_6')
        self.assertEqual(build_nested_cycle_deadlock_example().dfa.transitions['q_10', 'o1'], 'q_6')
        self.assertEqual(old.transitions['q_2', 'o1'], 'q_0')
        self.assertEqual(build_small_cycle_example().dfa.transitions['q_2', 'a'], 'q_0')

    def test_feasibility_and_root_maximal_patterns_need_different_depths(self):
        p = paper_small_figure().dfa;pre = preprocess(p);off = solve_offline(p)
        shallow = solve_limited_lookahead(pre, horizon=5);deep = solve_limited_lookahead(pre, horizon=6)
        validate_policy(pre, shallow);validate_policy(pre, deep)
        self.assertEqual(shallow.status, 'winning')
        self.assertEqual(shallow.maximal_patterns, (frozenset({'a', 'o2'}),))
        self.assertNotEqual(shallow.maximal_patterns, off.maximal_patterns)
        self.assertEqual(deep.maximal_patterns, off.maximal_patterns)
        self.assertEqual(off.maximal_patterns, (frozenset({'a', 'b', 'o2'}),))

    def test_archived_component_labels_change_solvability(self):
        self.assertEqual(solve_offline(archived_component_figure().dfa).status, 'losing')
        self.assertEqual(solve_offline(build_small_cycle_example().dfa).status, 'winning')

    def test_observation_rebuilds_a_window_around_the_full_new_estimate(self):
        p = paper_small_figure().dfa;pre = preprocess(p)
        fixed = solve_limited_lookahead(pre, horizon=5)
        first = complete_choice(p, frozenset(('q_0',)), p.controllable)
        estimate = dict(first.successors)['o1']
        self.assertEqual(estimate, frozenset(('q_6', 'q_8', 'q_11')))
        next_choice = complete_choice(p, estimate, frozenset(('a',)))
        self.assertEqual(next_choice.closure, frozenset(('q_6', 'q_7', 'q_8', 'q_9', 'q_10', 'q_11')))
        recentered = solve_limited_lookahead(pre, estimate=estimate, horizon=5)
        self.assertNotIn('q_10', fixed.window)
        self.assertIn('q_10', recentered.window)
        self.assertEqual(recentered.status, 'winning')
        validate_policy(pre, recentered)


if __name__ == '__main__':unittest.main()
