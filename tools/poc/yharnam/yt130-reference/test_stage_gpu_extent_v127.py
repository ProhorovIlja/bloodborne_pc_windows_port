"""Upstream YT #452/shadPS4 #5524 source-pinned client GPU extent regression."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "yt130_gpu_extent", Path(__file__).with_name("stage_gpu_extent_v127.py"))
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GpuExtentTests(unittest.TestCase):
    def setUp(self):
        self.header = mod.OLD_STRUCT
        self.cpp = (
            "    " + mod.OLD_RECREATE + "\n"
            "    if (" + mod.OLD_EXPAND + "\n"
        )

    def test_copies_exact_both_dimension_comparison(self):
        header, cpp = mod.rewrite(self.header, self.cpp)
        self.assertIn("levels >= other.levels && layers >= other.layers", header)
        self.assertIn(mod.NEW_RECREATE, cpp)
        self.assertIn(mod.NEW_EXPAND, cpp)
        self.assertNotIn(mod.OLD_RECREATE, cpp)
        self.assertNotIn(mod.OLD_EXPAND, cpp)

    def test_duplicate_and_drift_rejected(self):
        h, c = mod.rewrite(self.header, self.cpp)
        with self.assertRaises(ValueError):
            mod.rewrite(h, c)
        with self.assertRaises(ValueError):
            mod.rewrite(self.header.replace("operator<=>", "operator=="), self.cpp)
        with self.assertRaises(ValueError):
            mod.rewrite(self.header, self.cpp.replace(mod.OLD_EXPAND, "different layout"))

    def test_no_server_or_gameplay_protocol_changes(self):
        self.assertTrue(mod.HEADER.startswith("bbport/gpu/"))
        self.assertTrue(mod.CPP.startswith("bbport/gpu/"))
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")


if __name__ == "__main__":
    unittest.main()
