import json
import tempfile
import unittest
from pathlib import Path

from examples.basic.des_dfa_on_the_fly import (
    _clean_legacy_render_outputs,
    _read_branch_memory,
    _write_branch_memory,
)


class BranchMemoryTests(unittest.TestCase):
    def test_render_cleanup_preserves_branch_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = root / "物理分支选择记忆.json"
            memory.write_text('{"D(q_0,{q_0})": 3}\n', encoding="utf-8")
            (root / "ll_bts").mkdir()
            (root / "ll_bts" / "temporary.txt").write_text("x", encoding="utf-8")

            _clean_legacy_render_outputs(root)

            self.assertTrue(memory.exists())
            self.assertFalse((root / "ll_bts").exists())
            self.assertEqual(_read_branch_memory(memory), {"D(q_0,{q_0})": 3})

    def test_branch_memory_round_trip_and_invalid_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "物理分支选择记忆.json"
            _write_branch_memory(path, {"D0": 2, "D1": 5})
            self.assertEqual(_read_branch_memory(path), {"D0": 2, "D1": 5})

            path.write_text(json.dumps({"D0": "7", "bad": "x"}), encoding="utf-8")
            self.assertEqual(_read_branch_memory(path), {"D0": 7})


if __name__ == "__main__":
    unittest.main()
