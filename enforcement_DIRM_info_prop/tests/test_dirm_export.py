import tempfile
import unittest
from pathlib import Path

from dirm import DIRMObserver, export_observer
from dirm.paper_example import example_3_plant


class DIRMExportTests(unittest.TestCase):
    def test_export_writes_a_png_and_a_complete_text_listing(self):
        observer = DIRMObserver(
            example_3_plant(), observable={"a", "b"}, unobservable={"u"},
            releasable={"h"}, release_states={5, 9},
        )
        with tempfile.TemporaryDirectory() as directory:
            text_path, image_path = export_observer(observer, directory, "observer")
            self.assertTrue(text_path.is_file())
            self.assertTrue(image_path.is_file())
            self.assertIn("States", text_path.read_text(encoding="utf-8"))
            self.assertIn("Transitions", text_path.read_text(encoding="utf-8"))
            self.assertEqual(image_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
