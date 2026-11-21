"""Example 5 high/low BTS comparison regressions."""

import unittest

from bts_comparasion import YState, ZState, build_example_5_comparison


class Example5AICComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.high = build_example_5_comparison("high")
        cls.low = build_example_5_comparison("low")

    def test_high_is_original_and_low_is_augmented_without_release_labels(self):
        # Example 5 has a unique reachable N/Y copy of every plant state,
        # so suppressing the suffix in these figures does not merge nodes.
        self.assertEqual(
            len({state for state, _ in self.low.system.states}),
            len(self.low.system.states),
        )
        for bts in (self.high, self.low):
            self.assertEqual(bts.controllable, frozenset({"a"}))
            self.assertEqual(bts.uncontrollable, frozenset({"h", "o", "u"}))
            self.assertEqual(len(bts.control_patterns()), 2)
            for source, edges in bts.graph.items():
                if bts.mode == "high":
                    self.assertTrue(source.estimate <= bts.plant.states)
                else:
                    self.assertTrue(source.estimate <= bts.system.states)
                if isinstance(source, YState):
                    self.assertTrue(all(isinstance(edge.target, ZState) for edge in edges))
                else:
                    self.assertIn("o", source.gamma)
                    self.assertTrue(all(isinstance(edge.target, YState) for edge in edges))
                    self.assertTrue(all(edge.label in {"h", "o"} for edge in edges))

    def test_high_ur_and_low_release_path(self):
        full = self.high.plant.alphabet
        self.assertEqual(
            self.high.post_control(self.high.initial, full).estimate,
            frozenset({0, 5}),
        )
        self.assertEqual(
            self.low.post_control(self.low.initial, full).estimate,
            frozenset({
                (0, False), (5, False), (6, True), (7, True),
            }),
        )
        first_z = self.low.post_control(self.low.initial, full)
        after_h = next(
            edge.target for edge in self.low.post_observation(first_z)
            if edge.label == "h"
        )
        self.assertEqual(after_h.estimate, frozenset({(1, True), (8, True)}))
        second_z = self.low.post_control(after_h, full)
        self.assertEqual(
            second_z.estimate,
            frozenset({(1, True), (2, False), (3, True), (8, True)}),
        )
        after_o = next(
            edge.target for edge in self.low.post_observation(second_z)
            if edge.label == "o"
        )
        self.assertEqual(after_o.estimate, frozenset({(4, True), (9, False)}))

    def test_both_comparisons_merge_secret_and_nonsecret_after_o(self):
        high_z = ZState(frozenset({1, 2, 3, 8}), self.high.plant.alphabet)
        self.assertIn(
            YState(frozenset({4, 9})),
            {edge.target for edge in self.high.post_observation(high_z) if edge.label == "o"},
        )
        low_z = ZState(
            frozenset({(1, True), (2, False), (3, True), (8, True)}),
            self.low.plant.alphabet,
        )
        self.assertEqual(
            {edge.target for edge in self.low.post_observation(low_z) if edge.label == "o"},
            {YState(frozenset({(4, True), (9, False)}))},
        )
        self.assertEqual(
            [edge.label for edge in self.low.post_observation(low_z)], ["o"]
        )
        for bts, merged in (
            (self.high, YState(frozenset({4, 9}))),
            (self.low, YState(frozenset({(4, True), (9, False)}))),
        ):
            self.assertIn(merged, bts.graph)
            self.assertEqual(bts.synthesize().supervisor[bts.initial], bts.plant.alphabet)

    def test_disabling_a_keeps_o_but_cannot_cross_hidden_a_edges(self):
        gamma = frozenset({"h", "o", "u"})
        after_h = YState(frozenset({(1, True), (8, True)}))
        z = self.low.post_control(after_h, gamma)
        self.assertEqual(z.estimate, after_h.estimate)
        # Only the state-8 branch can execute the uncontrollable o.
        # The state-1 branch cannot cross the disabled a edge.
        self.assertEqual(
            {(edge.label, edge.target) for edge in self.low.post_observation(z)},
            {("o", YState(frozenset({(9, False)})))},
        )
        single = self.low.post_control(YState(frozenset({(1, True)})), gamma)
        self.assertEqual(single.estimate, frozenset({(1, True)}))
        self.assertFalse(self.low.post_observation(single))

    def test_control_reduction_preserves_distinct_nx_successors(self):
        for bts in (self.high, self.low):
            self.assertGreater(bts.reduction_stats["control_edges"], 0)
            for y, edges in bts.graph.items():
                if not isinstance(y, YState):
                    continue
                choices = [edge.target for edge in edges]
                for smaller in choices:
                    for larger in choices:
                        self.assertFalse(
                            smaller.gamma < larger.gamma
                            and smaller.estimate == larger.estimate
                            and bts.graph[smaller] == bts.graph[larger]
                        )


if __name__ == "__main__":
    unittest.main()
