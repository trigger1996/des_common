import unittest

from examples.non_deadlock import build_small_cycle_example, build_nested_cycle_deadlock_example
from paper_example_models import (paper_small_figure, paper_small_figure_original,
                                 paper_small_figure_hidden_chain_archive, archived_component_figure)
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, solve_offline, validate_policy, complete_choice
from des_core.closed_loop import build_closed_loop


class PaperExampleTests(unittest.TestCase):
    def test_r1_chain_changes_classification_but_not_the_retained_closed_loop(self):
        original = preprocess(paper_small_figure_original().dfa)
        revised = preprocess(paper_small_figure().dfa)

        for horizon in (4, 5):
            with self.subTest(horizon=horizon):
                before = solve_limited_lookahead(original, horizon=horizon)
                after = solve_limited_lookahead(revised, horizon=horizon)
                self.assertEqual(before.constructed_choices, after.constructed_choices)
                self.assertEqual(before.policy, after.policy)
                self.assertEqual(build_closed_loop(original, before), build_closed_loop(revised, after))

    def test_r1_figure_adds_only_the_requested_two_transitions(self):
        original = paper_small_figure_original().dfa
        plant = paper_small_figure().dfa
        self.assertEqual(plant.states - original.states, {'q_15', 'q_16'})
        self.assertEqual({k: v for k, v in plant.transitions.items() if k in original.transitions},
                         dict(original.transitions))
        self.assertEqual(set(plant.transitions) - set(original.transitions), {('q_14', 'a'), ('q_15', 'b')})
        pre = preprocess(plant)
        self.assertEqual(pre.Q_d, {'q_12', 'q_13', 'q_16'})
        self.assertEqual(pre.Q_f, {'q_14', 'q_15'})
        self.assertEqual(pre.lookahead_lower_bound, 4)
        self.assertEqual(plant.transitions['q_7', 'b'], 'q_12')

    def test_r1_observable_successors_are_complete_and_use_the_correct_event(self):
        plant = paper_small_figure().dfa
        initial = complete_choice(plant, frozenset({'q_0'}), plant.controllable)
        self.assertEqual(dict(initial.successors)['o1'], {'q_6', 'q_8', 'q_11'})
        local = complete_choice(plant, frozenset({'q_8'}), frozenset({'a', 'o2'}))
        self.assertEqual(dict(local.successors), {'o2': frozenset({'q_6', 'q_14'})})
        unsafe = complete_choice(plant, frozenset({'q_8'}), frozenset({'a', 'b'}))
        self.assertIn('q_13', unsafe.closure)
        pre = preprocess(plant)
        ll = solve_limited_lookahead(pre, horizon=5)
        self.assertEqual(ll.policy, solve_offline(plant).policy)
        validate_policy(pre, ll)

    def test_added_chain_and_its_deadlock_realize_structural_horizon_six(self):
        plant = paper_small_figure_hidden_chain_archive().dfa
        pre = preprocess(plant)
        self.assertEqual(pre.Q_f, frozenset(f'q_{i}' for i in range(15, 19)))
        self.assertEqual(pre.Q_o_tilde, frozenset({'q_6', 'q_8', 'q_11', 'q_14'}))
        self.assertEqual(pre.lookahead_lower_bound, 6)
        q = 'q_6'

        for event in ('a', 'b', 'u', 'u', 'u', 'u'):
            self.assertNotIn(event, plant.observable)
            q = plant.transitions[q, event]

        self.assertEqual(q, 'q_12')
        self.assertEqual(plant.enabled(q), ())

    def test_paper_variants_do_not_overwrite_current_models(self):
        small = paper_small_figure().dfa;old = archived_component_figure().dfa
        self.assertEqual(small.transitions['q_10', 'o2'], 'q_6')
        self.assertEqual(build_nested_cycle_deadlock_example().dfa.transitions['q_10', 'o1'], 'q_6')
        self.assertEqual(old.transitions['q_2', 'o1'], 'q_0')
        self.assertEqual(build_small_cycle_example().dfa.transitions['q_2', 'a'], 'q_0')

    def test_feasibility_and_root_maximal_patterns_need_different_depths(self):
        p = paper_small_figure().dfa;pre = preprocess(p);off = solve_offline(p)
        shallow = solve_limited_lookahead(pre, horizon=4);deep = solve_limited_lookahead(pre, horizon=5)
        validate_policy(pre, shallow);validate_policy(pre, deep)
        self.assertEqual(shallow.status, 'winning')
        self.assertEqual(shallow.maximal_patterns, (frozenset({'a', 'o2'}),))
        self.assertNotEqual(shallow.maximal_patterns, off.maximal_patterns)
        self.assertEqual(deep.maximal_patterns, off.maximal_patterns)
        self.assertEqual(off.maximal_patterns, (frozenset({'a', 'b', 'o2'}),))

    def test_original_figure_at_new_bound_retains_a_complete_recentered_continuation(self):
        p = paper_small_figure_original().dfa
        pre = preprocess(p)
        self.assertEqual(pre.Q_f, frozenset())
        self.assertEqual(pre.lookahead_lower_bound, 4)
        result = solve_limited_lookahead(pre)
        self.assertEqual(result.status, 'winning')
        self.assertNotIn('q_7', result.window)
        choice = next(c for c in result.policy[result.initial] if c.pattern == frozenset({'a', 'o2'}))
        self.assertEqual(dict(choice.successors)['o1'], frozenset({'q_6'}))
        self.assertEqual({c.closure for c in result.policy[frozenset({'q_6'})]}, {frozenset({'q_6', 'q_7'})})
        validate_policy(pre, result)

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
