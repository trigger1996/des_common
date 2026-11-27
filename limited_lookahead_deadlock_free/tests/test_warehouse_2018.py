import unittest

from des_core.automata import DFA
from des_core.warehouse_2018 import (solve_warehouse, truncate, exact_depth_states,
    supremal_controllable_nonblocking, synchronous_product)
from examples.warehouse_2018.models import paper_components, collision_free


class WarehouseReplicationTests(unittest.TestCase):
    def test_published_component_and_local_window_sizes(self):
        for current, expected in [((7, 4, 1), (7, 4, 7)), ((22, 27, 26), (4, 8, 4))]:
            components = paper_components(current)
            self.assertEqual([len(plant.states) for plant, _ in components], [34, 25, 25])
            self.assertEqual(tuple(len(truncate(plant, marked, plant.initial, 3)[0].states)
                                   for plant, marked in components), expected)

    def test_published_second_action_and_supervisor_size(self):
        result = solve_warehouse(paper_components((22, 27, 26)), legal=collision_free,
                                 interpretation='component-frontiers')
        self.assertEqual(result.gamma_c, frozenset({'15', '25'}))
        self.assertEqual(len(result.retained_states), 68)

    def test_first_action_and_disclosed_equation_difference(self):
        components = paper_components()
        component = solve_warehouse(components, legal=collision_free, interpretation='component-frontiers')
        equation = solve_warehouse(components, legal=collision_free, interpretation='equations')
        self.assertEqual(component.gamma_c, frozenset({'15', '23', '33', '35'}))
        self.assertIn('17', equation.gamma_c)
        self.assertNotIn('17', component.gamma_c)
        self.assertEqual(component.component_product_states, 196)
        self.assertLess(len(equation.window.states), 196)

    def test_exact_depth_keeps_cycle_endpoints(self):
        plant = DFA(frozenset('01'), '0', frozenset({'a'}), frozenset({'a'}),
                    frozenset({'a'}), {('0', 'a'): '1', ('1', 'a'): '0'})
        self.assertEqual(exact_depth_states(plant, '0', 2), frozenset({'0'}))

    def test_uncontrollable_predecessors_are_removed_recursively(self):
        plant = DFA(frozenset('0123'), '0', frozenset({'u', 'a'}), frozenset({'a'}),
                    frozenset({'u', 'a'}), {('0', 'u'): '1', ('1', 'u'): '2', ('2', 'u'): '3', ('2', 'a'): '2'})
        retained, _ = supremal_controllable_nonblocking(plant, frozenset('012'), frozenset('012'))
        self.assertFalse(retained)

    def test_marked_task_termination_is_not_silently_rejected_as_deadlock(self):
        plant = DFA(frozenset({'0'}), '0', frozenset(), frozenset(), frozenset(), {})
        result = solve_warehouse([(plant, plant.states)])
        self.assertEqual(result.status, 'local_supervisor')
        self.assertFalse(result.gamma_c)

    def test_partial_observation_is_not_treated_as_known_state(self):
        plant, marked = paper_components()[0]
        partial = DFA(plant.states, plant.initial, plant.events, plant.controllable, frozenset(), plant.transitions)

        with self.assertRaises(ValueError):
            solve_warehouse([(partial, marked)])

    def test_shared_event_requires_every_owner_to_enable_it(self):
        first = DFA(frozenset('01'), '0', frozenset({'a'}), frozenset({'a'}), frozenset({'a'}), {('0', 'a'): '1'})
        second = DFA(frozenset('01'), '0', frozenset({'a'}), frozenset({'a'}), frozenset({'a'}), {})
        product, _ = synchronous_product([(first, first.states), (second, second.states)])
        self.assertEqual(len(product.states), 1)
        self.assertFalse(product.transitions)

    def test_failed_replanning_does_not_execute_an_invented_fallback(self):
        from examples.warehouse_2018.warehouse_2018_case_study import validate_warehouse_execution

        plant = DFA(frozenset('012'), '0', frozenset({'b', 'u'}), frozenset({'b'}),
                    frozenset({'b', 'u'}), {('0', 'b'): '1', ('1', 'u'): '2'})
        result = validate_warehouse_execution([(plant, plant.states)], 1,
            interpretation='component-frontiers', max_states=100)
        self.assertEqual(result['execution_outcome'], 'replanning_failure')
        self.assertIsNone(result['deadlock_free'])
        self.assertEqual(result['empty_local_states'], [('1',)])
        self.assertEqual(result['transitions'], [[('0',), 'b', ('1',)]])
        self.assertFalse(result['deadlocks'])

    def test_control_induced_deadlock_is_distinct_from_replanning_failure(self):
        from examples.warehouse_2018.warehouse_2018_case_study import validate_warehouse_execution

        plant = DFA(frozenset('01'), '0', frozenset({'a'}), frozenset({'a'}),
                    frozenset({'a'}), {('0', 'a'): '1'})
        result = validate_warehouse_execution([(plant, plant.states)], 2,
            interpretation='component-frontiers', max_states=100)
        self.assertEqual(result['execution_outcome'], 'deadlocking')
        self.assertFalse(result['deadlock_free'])
        self.assertEqual(result['deadlocks'], [('0',)])
        self.assertFalse(result['empty_local_states'])


if __name__ == '__main__':
    unittest.main()
