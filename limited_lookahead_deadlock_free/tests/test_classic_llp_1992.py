"""Conformance checks for an independent classic LLP implementation."""

from dataclasses import replace
import random
import unittest

from des_core.automata import DFA
from des_core.classic_llp_1992 import solve_classic_llp, ClassicLLPBudgetExceeded


def plant(states, transitions, controls, initial='0'):
    events = frozenset(event for _, event in transitions)

    return DFA(frozenset(states), initial, events, frozenset(controls), events, transitions)


class ClassicLLPTests(unittest.TestCase):
    def test_controllable_branch_to_illegal_state_is_disabled(self):
        model = plant('012', {('0', 'a'): '1', ('0', 'b'): '2', ('1', 'a'): '1'}, {'a', 'b'})
        result = solve_classic_llp(model, horizon=2, legal=lambda q: q != '2')
        self.assertEqual(result.status, 'local_supervisor')
        self.assertEqual(result.gamma_c, frozenset({'a'}))

    def test_uncontrollable_illegality_propagates(self):
        model = plant('012', {('0', 'u'): '1', ('1', 'u'): '2', ('0', 'a'): '0'}, {'a'})
        result = solve_classic_llp(model, horizon=2, legal=lambda q: q != '2')
        self.assertEqual(result.status, 'empty_local_supervisor')

    def test_boundary_attitudes_and_no_hidden_liveness_modification(self):
        model = plant('01', {('0', 'a'): '1', ('1', 'a'): '1'}, {'a'})
        optimistic = solve_classic_llp(model, horizon=1)
        conservative = solve_classic_llp(model, horizon=1, attitude='conservative')
        self.assertEqual(optimistic.gamma_c, frozenset({'a'}))
        self.assertFalse(conservative.gamma_c)
        self.assertEqual(conservative.status, 'local_supervisor')

    def test_transient_marking_requires_a_retained_path_to_marker(self):
        model = plant('012', {('0', 'a'): '1', ('1', 'a'): '2'}, {'a'})
        result = solve_classic_llp(model, horizon=3, marked={'2'})
        self.assertEqual(result.gamma_c, frozenset({'a'}))
        result = solve_classic_llp(model, horizon=3, marked=set())
        self.assertEqual(result.status, 'empty_local_supervisor')

    def test_same_physical_state_at_different_depths_remains_distinct(self):
        model = plant('0', {('0', 'a'): '0'}, {'a'})
        self.assertEqual(solve_classic_llp(model, horizon=4).stored_states, 5)

    def test_depth_sharing_matches_full_event_prefix_tree(self):
        rng = random.Random(199212)

        for _ in range(80):
            transitions = {(str(q), e): str(rng.randrange(4)) for q in range(4)
                           for e in ('a', 'b', 'u') if rng.random() < 0.7}
            model = plant('0123', transitions, {'a', 'b'})

            for attitude in ('optimistic', 'conservative'):
                for horizon in (1, 2, 3, 4):
                    options = dict(horizon=horizon, legal=lambda q: q != '3', marked={'0', '2'}, attitude=attitude)
                    shared = solve_classic_llp(model, **options)
                    tree = solve_classic_llp(model, share_same_depth=False, **options)
                    self.assertEqual((shared.status, shared.gamma_c), (tree.status, tree.gamma_c))

    def test_partial_observation_and_exhausted_budget_are_not_losing(self):
        model = plant('01', {('0', 'a'): '1', ('1', 'a'): '0'}, {'a'})

        with self.assertRaises(ValueError):
            solve_classic_llp(replace(model, observable=frozenset()), horizon=1)

        with self.assertRaises(ClassicLLPBudgetExceeded):
            solve_classic_llp(model, horizon=5, max_states=2)


if __name__ == '__main__':
    unittest.main()
