import tempfile
import unittest
from pathlib import Path

from dirm import (
    build_untimed_iwa_augmented,
    export_augmented_system,
    write_augmented_comparison,
)
from dirm.augmented_export import _edge_label


class AugmentedDIRMExportTests(unittest.TestCase):
    def test_augmentation_lifts_plant_edges_without_ur_nx_or_control(self):
        system = build_untimed_iwa_augmented()

        self.assertIsNone(system.step(("0", False), "a"))
        self.assertIsNone(system.step(("0", False), "b"))
        self.assertEqual(system.step(("0", False), "h2"), ("6", True))
        self.assertEqual(
            _edge_label(("0", False), ("6", True), ["h2"]),
            "0N --h2--> 6Y",
        )
        self.assertEqual(
            _edge_label(("2", True), ("3", False), ["a", "b"]),
            "2Y --a, b--> 3N",
        )

    def test_export_writes_all_states_and_transitions(self):
        system = build_untimed_iwa_augmented()
        with tempfile.TemporaryDirectory() as directory:
            text_path, image_path = export_augmented_system(
                system, directory, "augmented"
            )
            listing = text_path.read_text(encoding="utf-8")
            self.assertIn("DIRM augmented transition system", listing)
            self.assertIn("State space: BFS reachable from initial", listing)
            self.assertIn("Counts: states=10, reachable=10, transitions=16", listing)
            self.assertIn("0N  [initial]", listing)
            self.assertIn("2Y  [true release]", listing)
            self.assertIn("5Y  [true release]", listing)
            self.assertIn("3Y  [SECRET]", listing)
            self.assertNotIn("0Y", listing)
            self.assertIn("0N --h1--> 1Y", listing)
            self.assertEqual(image_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_legacy_product_export_corresponds_to_bfs_restriction(self):
        system = build_untimed_iwa_augmented()
        self.assertEqual(len(system.product_states), 14)
        self.assertEqual(len(system.states), 10)
        with tempfile.TemporaryDirectory() as directory:
            text_path, _ = export_augmented_system(
                system, directory, "legacy", include_unreachable=True
            )
            listing = text_path.read_text(encoding="utf-8")
            self.assertIn("State space: full product Q x {N,Y}", listing)
            self.assertIn("Counts: states=14, reachable=10, transitions=22", listing)
            self.assertIn("1N  [unreachable]", listing)
            comparison = write_augmented_comparison(
                system, Path(directory) / "comparison.txt"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "Reachable subsystem corresponds to product restriction: True",
                comparison,
            )


if __name__ == "__main__":
    unittest.main()
