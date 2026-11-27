import unittest

from des_core.comparison_averages import decision_metrics, comparison_averages


class ComparisonAverageTests(unittest.TestCase):
    def test_timeout_is_not_an_infeasibility_proof(self):
        self.assertFalse(decision_metrics('winning', 'budget_exceeded')['decision_comparison_complete'])
        self.assertFalse(decision_metrics('inconclusive', 'inconclusive')['same_solvability_result'])
        self.assertTrue(decision_metrics('losing', 'losing')['offline_losing_implies_online_losing'])
        self.assertFalse(decision_metrics('winning', 'losing')['same_solvability_result'])

    def test_model_medians_and_raw_repetition_means_stay_distinct(self):
        rows = [];details = {}

        for name, on, off, mem_on, mem_off in (('a', 1., 2., 20, 10), ('b', 3., 2., 10, 30)):
            rows.append(dict(name=name, online_total_median_seconds=on, offline_median_seconds=off,
                online_peak_python_bytes=mem_on, offline_peak_python_bytes=mem_off, online_nodes=1, offline_nodes=2,
                time_saving_including_pre=(off-on)/off, peak_memory_saving=(mem_off-mem_on)/mem_off, node_saving=.5,
                **decision_metrics('losing', 'losing')))
            details[name] = dict(samples=dict(pre_seconds=[0, 0, 0], online_seconds=[on, on, 30], offline_seconds=[off, off, off]))

        result = comparison_averages(rows, details);a = result['arithmetic_means']
        self.assertEqual(a['online_mean_model_median_seconds'], 2.)
        self.assertEqual(a['online_raw_mean_seconds'], 34/3)
        self.assertEqual(a['online_mean_peak_python_bytes'], 15)
        self.assertEqual(result['negative_savings']['counts'], dict(time=1, memory=1, nodes=0))
        self.assertEqual(result['decision_agreement']['equal_decisions'], 2)


if __name__ == '__main__':unittest.main()
