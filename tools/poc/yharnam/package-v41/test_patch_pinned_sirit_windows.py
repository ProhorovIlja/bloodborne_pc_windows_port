"""Original pinned Sirit stream.h CLANG64 fail-closed patch tests."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

p=Path(__file__).with_name("patch_pinned_sirit_windows.py")
spec=importlib.util.spec_from_file_location("sirit_win",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ORIGINAL="""/* This file is part of the sirit project.
 * 3-Clause BSD License
 */
#pragma once
#include <bit>
#include <cassert>
#include <concepts>
void f() { std::abort(); }
"""

class SiritWindowsTests(unittest.TestCase):
    def test_narrow_include_with_no_runtime_changes(self):
        result=m.patch_source(ORIGINAL)
        self.assertIn("#include <cassert>\n#include <cstdlib>",result)
        self.assertEqual(result.replace(m.NEW,m.OLD),ORIGINAL)
        self.assertEqual(result.count("std::abort();"),1)

    def test_replay_and_unknown_pinned_source_refused(self):
        for bad in (m.patch_source(ORIGINAL),
                    ORIGINAL.replace("std::abort();","abort();"),
                    ORIGINAL.replace("3-Clause BSD License","private"),
                    ORIGINAL.replace("#include <cassert>","")):
            with self.subTest(source=bad[:65]):
                with self.assertRaises(ValueError): m.patch_source(bad)

    def test_file_sha_and_no_mutation_on_drift(self):
        with TemporaryDirectory() as directory:
            f=Path(directory)/"stream.h"
            f.write_text(ORIGINAL,encoding="utf-8")
            before=f.read_bytes()
            with self.assertRaisesRegex(ValueError,"Wrong original Sirit git blob"):
                m.patch_file(f)
            self.assertEqual(f.read_bytes(),before)

    def test_blob_hash(self):
        self.assertEqual(m.git_blob(b"test"),"30d74d258442c7c65512eafab474568dd706c430")

if __name__=="__main__":
    unittest.main()
