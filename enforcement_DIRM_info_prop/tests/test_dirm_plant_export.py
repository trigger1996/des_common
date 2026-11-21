import tempfile
import unittest

from dirm import (
    example_3_plant,
    example_4_plant,
    example_5_plant,
    example_6_plant,
    export_plant,
    simplified_example_2_plant,
    user_example_1_plant,
)


class DIRMPlantExportTests(unittest.TestCase):
    def test_all_maintained_layouts_export_the_original_plant(self):
        examples = (
            (user_example_1_plant(), "example_1"),
            (simplified_example_2_plant(), "example_2"),
            (example_3_plant(), "example_3"),
            (example_4_plant(), "example_4"),
            (example_5_plant(), "example_5"),
            (example_6_plant(), "example_6"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (plant, layout) in enumerate(examples):
                text_path, image_path = export_plant(
                    plant, directory, f"plant_{index}", layout=layout
                )
                listing = text_path.read_text(encoding="utf-8")
                self.assertIn("Original DFA plant", listing)
                self.assertIn(f"States: {len(plant.states)}", listing)
                self.assertIn(f"q_{plant.initial}", listing)
                self.assertEqual(image_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_example_1_and_simplified_example_2_transitions(self):
        example_1 = user_example_1_plant()
        example_2 = simplified_example_2_plant()

        self.assertEqual(example_1.initial, "0")
        self.assertEqual(example_2.initial, "0")
        self.assertEqual(example_1.transitions[("2", "a")], "3")
        self.assertNotIn(("2", "b"), example_1.transitions)
        self.assertEqual(example_1.transitions[("4", "o")], "3")

        self.assertEqual(example_2.transitions[("2", "a")], "3")
        self.assertNotIn(("2", "b"), example_2.transitions)
        self.assertNotIn(("4", "o"), example_2.transitions)
        self.assertEqual(
            example_2.states, {"0", "1", "2", "3", "4", "5", "6"}
        )
        self.assertEqual(len(example_2.transitions), 11)
        self.assertEqual(example_2.secret_states, {"5", "6"})
        self.assertFalse(any(
            source in example_2.secret_states and target in example_2.secret_states
            for (source, _), target in example_2.transitions.items()
        ))
        self.assertNotIn(("0", "o"), example_2.transitions)
        self.assertEqual(example_2.transitions[("0", "h")], "1")
        self.assertEqual(example_2.transitions[("0", "uc")], "6")
        self.assertEqual(example_2.transitions[("6", "o")], "2")
        self.assertEqual(example_2.transitions[("3", "uc")], "4")
        self.assertEqual(example_2.transitions[("4", "b")], "5")
        self.assertNotIn(("4", "h"), example_2.transitions)
        self.assertEqual(example_2.transitions[("4", "a")], "6")
        self.assertEqual(example_2.transitions[("5", "o")], "3")
        self.assertEqual(example_2.transitions[("6", "h")], "4")


if __name__ == "__main__":
    unittest.main()
