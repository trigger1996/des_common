import unittest

from graph_size_metrics import graph_size_metrics, aggregate_graph_sizes


def storage(d, o, rd=0, ro=0):
    return dict(D=d, O=o, nodes=d+o, retained_D=rd, retained_O=ro)


class GraphSizeTests(unittest.TestCase):
    def test_aggregate_uses_ratio_of_sums_and_keeps_retained_separate(self):
        rows = [graph_size_metrics(storage(1, 0, 1, 0), storage(1, 9, 1, 4)),
              graph_size_metrics(storage(1, 4, 1, 1), storage(1, 0, 1, 0))]
        result = aggregate_graph_sizes(rows)
        self.assertEqual(result['online_nodes'], 6)
        self.assertEqual(result['offline_nodes'], 11)
        self.assertAlmostEqual(result['node_saving'], 5/11)
        self.assertEqual(rows[1]['nodes_saved'], -4)
        self.assertEqual(result['online_retained_nodes'], 3)
        self.assertEqual(result['offline_retained_nodes'], 6)
        self.assertIsNone(graph_size_metrics(storage(1, 0), storage(1, 1))['retained_node_saving'])

    def test_inconsistent_logical_node_total_is_rejected(self):
        bad = storage(2, 3);bad['nodes'] = 8

        with self.assertRaises(AssertionError):graph_size_metrics(bad, storage(1, 1))


if __name__ == '__main__':unittest.main()
