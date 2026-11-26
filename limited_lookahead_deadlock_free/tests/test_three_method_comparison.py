import unittest

from three_method_comparison import (METHODS, components_for, input_hash, calculate,
                                     validate_execution, sample_trajectory)


class CommonExampleTests(unittest.TestCase):
    def test_same_ring_example_has_three_verified_deadlock_free_controllers(self):
        components = components_for('Ring2-FO')
        digest = input_hash(components)

        for method in METHODS:
            result = validate_execution(method, components, 3)
            self.assertTrue(result['deadlock_free'], method)
            self.assertEqual(result['plant_states'], 10)
            self.assertEqual(result['visited_states'], 9)
            self.assertTrue(all(event != 'fail' for _, event, _ in result['transitions']))
            self.assertEqual(input_hash(components), digest)

    def test_short_window_failures_are_distinct_from_global_losing(self):
        components = components_for('E2-FO')

        for method in ('cai2018', 'llp1992'):
            result = validate_execution(method, components, 3)
            self.assertEqual(result['outcome'], 'replanning_failure')
            self.assertTrue(result['witnesses'])
            self.assertFalse(result['deadlock_free'])

        self.assertTrue(validate_execution('ours', components, 3)['deadlock_free'])

    def test_larger_common_horizon_restores_all_three_continuations(self):
        components = components_for('E2-FO')

        for method in METHODS:
            self.assertTrue(validate_execution(method, components, 16)['deadlock_free'], method)

    def test_marked_nonblocking_and_deadlock_free_are_checked_separately(self):
        components = components_for('Fig1-FO')

        for method in ('cai2018', 'llp1992'):
            self.assertEqual(calculate(method, components, 8)['root_status'], 'local_supervisor')
            self.assertEqual(validate_execution(method, components, 8)['outcome'], 'deadlocking')

    def test_real_trajectory_uses_new_solves_and_records_the_event_cap(self):
        components = components_for('Ring2-FO')
        traces = [sample_trajectory(method, components, 3, cap=5) for method in METHODS]

        for trace in traces:
            self.assertEqual(trace['executed_events'], 5)
            self.assertEqual(trace['stop'], 'observation_cap')
            self.assertGreater(trace['cumulative_solve_seconds'], 0)

        self.assertEqual([[row['event'] for row in trace['steps']] for trace in traces],
                         [[row['event'] for row in traces[0]['steps']]] * 3)


if __name__ == '__main__':
    unittest.main()
