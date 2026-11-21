import tempfile
import unittest
from pathlib import Path

from dirm import (
    BTSEdge, IState, JState, LState,
    build_user_example_1_bts, build_simplified_example_2_bts,
    build_example_3_bts, build_example_4_bts, build_example_5_bts,
)
from dirm.supervisory_export import supervisory_diagnostics, write_supervisory_text
from dirm.augmented_export import write_augmented_text
from dirm.plant_export import write_plant_text


class DIRMStateClassificationTests(unittest.TestCase):
    def test_pruning_rounds_distinguish_safety_seeds_from_inconsistency(self):
        bts = build_simplified_example_2_bts()
        full = bts.plant.alphabet
        other = full - {"b"}
        estimate = lambda q: frozenset({(q, False)})
        bad_i = bts.initial
        good_i = IState(estimate("2"), estimate("2"))
        choice_i = IState(estimate("3"), estimate("3"))
        bad_j = JState(estimate("5"), estimate("5"), full)
        dependent_j = JState(estimate("0"), estimate("0"), full)
        terminal_j = JState(estimate("2"), estimate("2"), other)
        secret_l = LState(frozenset({("5", True)}), full)
        dependent_l = LState(frozenset({("2", True)}), full)
        bts.graph = {
            bad_i: (BTSEdge(bad_j, "IJ", gamma=full),),
            good_i: (BTSEdge(terminal_j, "IJ", gamma=other),),
            choice_i: (BTSEdge(dependent_j, "IJ", gamma=full),
                       BTSEdge(terminal_j, "IJ", gamma=other)),
            bad_j: (), dependent_j: (BTSEdge(secret_l, "JL", sigma="b"),),
            terminal_j: (), secret_l: (),
            dependent_l: (BTSEdge(bad_i, "LI"),),
        }
        result = bts.synthesize()
        self.assertEqual(result.secret_revealing_states, {bad_j})
        self.assertEqual(result.secret_only_states, {bad_j, secret_l})
        self.assertEqual(result.inconsistent_states, {bad_i, dependent_j, dependent_l})
        self.assertEqual(result.removal_rounds[bad_j], 0)
        self.assertEqual(result.removal_rounds[bad_i], 1)
        self.assertEqual(result.removal_rounds[dependent_j], 1)
        self.assertEqual(result.removal_rounds[dependent_l], 2)
        self.assertEqual(result.blocked_successors[dependent_l], {bad_i})
        self.assertIn(terminal_j, result.winning_states)  # J deadlock is allowed by (ii).
        self.assertIn(choice_i, result.winning_states)   # A single remaining choice suffices.
        self.assertEqual(result.policy[choice_i], {other})

    def test_classification_preserves_previous_winning_region_for_all_examples(self):
        for builder in (build_user_example_1_bts, build_simplified_example_2_bts,
                        build_example_3_bts, build_example_4_bts, build_example_5_bts):
            bts = builder()
            expected = {q for q in bts.graph if not bts.is_revealing(q)}
            while True:
                previous = set(expected)
                for q in tuple(expected):
                    edges = bts.graph[q]
                    keep = (any(e.target in expected for e in edges) if isinstance(q, IState)
                            else all(e.target in expected for e in edges) if isinstance(q, JState)
                            else len(edges) == 1 and edges[0].target in expected)
                    if not keep:
                        expected.remove(q)
                if expected == previous:
                    break
            result = bts.synthesize()
            self.assertEqual(result.winning_states, expected)
            self.assertFalse(result.secret_only_states & result.inconsistent_states)
            self.assertEqual(set(bts.graph), result.winning_states |
                             result.secret_only_states | result.inconsistent_states)
            for q, causes in result.blocked_successors.items():
                for cause in causes:
                    self.assertLess(result.removal_rounds[cause], result.removal_rounds[q])

    def test_text_reports_identify_secret_states_and_explain_removals(self):
        bts = build_simplified_example_2_bts()
        result = bts.synthesize()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            listing = write_supervisory_text(bts, result, root / "tts.txt").read_text(encoding="utf-8")
            report = supervisory_diagnostics(bts, result)
            self.assertIn(report, listing)
            self.assertIn("SECRET-REVEALING J states", listing)
            self.assertIn("INCONSISTENT states", listing)
            self.assertIn("removed successors:", listing)
            self.assertIn("removal round =", listing)
            plant = write_plant_text(bts.plant, root / "dfa.txt").read_text(encoding="utf-8")
            augmented = write_augmented_text(bts.system, root / "aug.txt").read_text(encoding="utf-8")
            self.assertIn("q_5 [SECRET]", plant)
            self.assertIn("5Y  [true release, SECRET]", augmented)
            self.assertIn("6N  [SECRET]", augmented)


if __name__ == "__main__":
    unittest.main()
