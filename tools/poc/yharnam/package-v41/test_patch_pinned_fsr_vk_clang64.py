"""Pinned AMD FSR vk.cpp compatibility tests, no live game or proprietary assets."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

p=Path(__file__).with_name("patch_pinned_fsr_vk_clang64.py")
spec=importlib.util.spec_from_file_location("fsr_vk_fix",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ORIGINAL = """// Copyright (C) 2024 Advanced Micro Devices, Inc.
#include <FidelityFX/host/ffx_interface.h>
#include <ffx_breadcrumbs_list.h>
void init(BackendContext* backendContext) {
    new (&backendContext->uniformBufferMutex) std::mutex();
}
void mips(Resource* resourceDesc) {
    resourceDesc->mipCount = floor(log2(FFX_MAXIMUM(64, 32)));
}
"""

class PinnedFsrVkTests(unittest.TestCase):
    def test_standard_headers_and_qualified_math_only(self):
        after=m.patch_text(ORIGINAL)
        self.assertIn("#include <cmath>\n#include <new>\n",after)
        self.assertEqual(after.count("std::floor(std::log2("),1)
        self.assertEqual(after.replace(m.INCLUDES,"").replace(m.FIXED_LOG2,m.LOG2),ORIGINAL)
        self.assertIn("new (&backendContext->uniformBufferMutex) std::mutex();",after)

    def test_drift_duplicate_and_double_patch_are_refused(self):
        bad=[ORIGINAL+ORIGINAL, ORIGINAL.replace(m.HEADER,""),
             ORIGINAL.replace("log2(","log10("),
             ORIGINAL.replace("new (&backendContext","new (backendContext"),
             m.patch_text(ORIGINAL)]
        for candidate in bad:
            with self.subTest(candidate=candidate[:45]):
                with self.assertRaises(ValueError): m.patch_text(candidate)

    def test_unpinned_file_never_mutated(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"ffx_vk.cpp"
            p.write_text(ORIGINAL,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"blob mismatch"):
                m.patch_file(p)
            self.assertEqual(p.read_text(),ORIGINAL)

    def test_blob_determinism(self):
        self.assertEqual(m.git_blob(b"test"),"30d74d258442c7c65512eafab474568dd706c430")
        self.assertEqual(len(m.ORIGINAL_BLOB),40)

if __name__=="__main__":
    unittest.main()
