import tempfile
import unittest

from dirm import (
    build_simplified_example_2_bts,
    build_untimed_iwa_bts,
    export_supervisory_bts,
)
from dirm.supervisory_export import write_supervisory_text


class SupervisoryDIRMExportTests(unittest.TestCase):
    def test_export_writes_tripartite_graph_and_complete_listing(self):
        bts = build_untimed_iwa_bts()
        result = bts.synthesize()
        with tempfile.TemporaryDirectory() as directory:
            text_path, image_path = export_supervisory_bts(
                bts, directory, "supervisory", result=result
            )
            listing = text_path.read_text(encoding="utf-8")
            self.assertIn("Structure: I-J-(I|L)-I", listing)
            self.assertIn("I/J contain q_hat and q only", listing)
            self.assertIn("I0: {0N}, {0N} --gamma=", listing)
            self.assertIn("--> J0:", listing)
            self.assertIn("J0:", listing)
            self.assertIn("L0:", listing)
            self.assertIn("--epsilon--> I", listing)
            self.assertNotIn("I0 --gamma=", listing)
            self.assertNotIn("actual =", listing)
            self.assertEqual(image_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_example_2_release_labels_show_h_cycle_once(self):
        bts = build_simplified_example_2_bts()
        with tempfile.TemporaryDirectory() as directory:
            path = write_supervisory_text(
                bts, bts.synthesize(), f"{directory}/example_2.txt"
            )
            lines = path.read_text(encoding="utf-8").splitlines()
        j0 = [line for line in lines if line.startswith("J0: {0N, 6N}")]
        self.assertEqual(sum("--h--> L1:" in line for line in j0), 1)
        self.assertEqual(sum("--hh^+--> L2:" in line for line in j0), 1)
        self.assertEqual(sum("--h^+o--> L0:" in line for line in j0), 1)


if __name__ == "__main__":
    unittest.main()
