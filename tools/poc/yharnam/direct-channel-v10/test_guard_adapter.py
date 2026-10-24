#!/usr/bin/env python3
import unittest
import zipfile
from pathlib import Path
from guard_adapter import patch_adapter
ROOT=Path(__file__).resolve().parent.parent
V7=ROOT/"pinned-archives"/"SH-YT-NATIVE-DIRECT-P2P-V7-20261023.zip"
class GuardAdapterTests(unittest.TestCase):
    def setUp(self):
        with zipfile.ZipFile(V7) as z:
            self.source=z.read("native_shlk_adapter.hpp").decode("utf-8")
    def test_two_gate_sites_and_header(self):
        s=patch_adapter(self.source)
        self.assertEqual(s.count("DirectSafeGameFrame"),2)
        self.assertIn('#include "native_direct_filter.hpp"',s)
        self.assertIn("return {}; // preserve shadNet server channel policy",s)
    def test_double_instrumentation_refused(self):
        with self.assertRaises(ValueError):
            patch_adapter(patch_adapter(self.source))
    def test_pinned_anchor_changed_refused(self):
        with self.assertRaises(ValueError):
            patch_adapter(self.source.replace("      out.data=std::move(received);",""))
if __name__=="__main__":
    unittest.main()
