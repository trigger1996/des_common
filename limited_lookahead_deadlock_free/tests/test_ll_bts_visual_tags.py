import unittest

from des_dfa_on_the_fly import (
    _initial_physical_successor_candidates,
    _ll_bts_node_tag,
    _physical_ll_bts_snapshots,
)
from des_core.limited_lookahead import post_leq
from des_core.ll_bts import admissible_control_patterns, controlled_unobservable_reach, observable_next
from examples.non_deadlock import all_examples


class LLBTSVisualTagsTests(unittest.TestCase):
    def setUp(self):
        self.example = next(e for e in all_examples() if e.name ==
                            "example2_nested_cycles_deadlock_full_partial_observation")
        self.plant = self.example.original_dfa
        self.lookahead = post_leq(self.plant, frozenset({self.plant.initial}),
                                 self.example.lookahead_limit)

    def test_deadlock_takes_precedence_over_control_inconsistency(self):
        window = post_leq(self.plant, frozenset({self.plant.initial}), 6)
        for label in ("D(q_6,{q_12,q_6,q_7})",
                      "O({q_12,q_6,q_7},{a,b,o})",
                      "O({q_12,q_6,q_7},{a,b})"):
            with self.subTest(label=label):
                self.assertEqual(_ll_bts_node_tag(self.plant, label, window), "N")
        self.assertEqual(_ll_bts_node_tag(self.plant, "O({q_6},{})", window), "Y")
        self.assertEqual(_ll_bts_node_tag(self.plant, "O({q_6,q_7},{a,o})", window), "Y")

    def test_branch_four_deadlock_nodes_are_bad_and_never_unknown(self):
        snapshots = _physical_ll_bts_snapshots(
            self.plant, 6, {},
            forced_choices={"D(q_0,{q_0})": 3},
        )
        found = set()
        for snapshot in snapshots:
            deadlocked = {node for node in snapshot.known_nodes if "q_12" in node}
            found.update(deadlocked)
            self.assertTrue(deadlocked <= snapshot.no)
            self.assertTrue(deadlocked.isdisjoint(snapshot.unknown))
        # With u=5, q_12 lies outside the local lookahead window. If a
        # concrete deadlock is represented in a future window, it must still
        # be classified as bad rather than merely inconsistent.

    def test_physical_arrival_reinitializes_window_and_estimate(self):
        candidates = _initial_physical_successor_candidates(self.plant, 5)
        q8_choice = next(
            index for index, candidate in enumerate(candidates)
            if candidate[3][0] == "q_8"
        )
        snapshots = _physical_ll_bts_snapshots(
            self.plant, 5, {},
            forced_choices={"D(q_0,{q_0})": q8_choice},
        )
        second_round = snapshots[2]
        self.assertIn("D(q_8,{q_8})", second_round.known_nodes)
        q13_nodes = {node for node in second_round.known_nodes if "q_13" in node}
        self.assertTrue(q13_nodes)
        self.assertTrue(q13_nodes <= second_round.no)

    def test_mandatory_u_closure_and_all_eight_patterns(self):
        patterns = {p | self.plant.uncontrollable for p in admissible_control_patterns(self.plant)}
        self.assertEqual(len(patterns), 8)
        self.assertIn(frozenset({"o1", "u"}), patterns)
        self.assertIn(frozenset({"a", "b", "o1", "u"}), patterns)
        reach = controlled_unobservable_reach(
            self.plant, frozenset({"q_6", "q_8", "q_11"}),
            frozenset({"u", "o1"}),
            post_leq(self.plant, frozenset({self.plant.initial}), 6))
        self.assertEqual(reach, frozenset({"q_6", "q_8", "q_11", "q_9"}))
        self.assertEqual(observable_next(
            self.plant, reach, "o",
            post_leq(self.plant, frozenset({self.plant.initial}), 6)),
                         frozenset())
        self.assertEqual(observable_next(
            self.plant, reach, "o1",
            post_leq(self.plant, frozenset({self.plant.initial}), 6)),
                         frozenset({"q_6"}))
        self.assertEqual(observable_next(
            self.plant, reach, "o2",
            post_leq(self.plant, frozenset({self.plant.initial}), 6)),
                         frozenset({"q_14"}))

    def test_horizon_five_excludes_q11_boundary_successor(self):
        window = post_leq(self.plant, frozenset({self.plant.initial}), 5)
        self.assertNotIn("q_11", window)
        snapshots = _physical_ll_bts_snapshots(self.plant, 5, {},
                                                forced_choices={"D(q_0,{q_0})": 0})
        self.assertNotIn("D(q_11,{q_11,q_6,q_8})", snapshots[1].known_nodes)


if __name__ == "__main__":
    unittest.main()

