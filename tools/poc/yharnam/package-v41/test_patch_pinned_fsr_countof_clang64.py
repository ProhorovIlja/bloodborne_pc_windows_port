"""Source-pinned AMD FSR opticalflow/frame interpolation Windows CLANG64 tests."""
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

p=Path(__file__).with_name("patch_pinned_fsr_countof_clang64.py")
spec=importlib.util.spec_from_file_location("fsr_countof",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
HDR="// Copyright (C) 2024 Advanced Micro Devices, Inc.\n"

class FsrCountofTest(unittest.TestCase):
    def test_exact_array_semantics_and_pinned_counts(self):
        source=HDR+"_countof(myArr); _countof(copyJobs); _countof(myArr);"
        fixed=m.patch_source(source,3)
        self.assertIn("(sizeof(myArr) / sizeof((myArr)[0]))",fixed)
        self.assertEqual(fixed.count("sizeof((myArr)[0])"),2)
        self.assertEqual(fixed.count("sizeof((copyJobs)[0])"),1)
        self.assertNotIn("_countof(",fixed)
        self.assertEqual(m.SOURCE["opticalflow/ffx_opticalflow.cpp"][1],9)
        self.assertEqual(m.SOURCE["frameinterpolation/ffx_frameinterpolation.cpp"][1],14)

    def test_double_patch_missing_marker_and_unexpected_macro_refused(self):
        source=HDR+"_countof(copyJobs);"
        invalid=[source+"_countof(extra);",
                 source.replace("_countof(copyJobs)","_countof(a.b)"),
                 source.replace("2024 Advanced Micro Devices","2025 unknown"),
                 m.patch_source(source,1)]
        for s in invalid:
            with self.subTest(input=s[:70]):
                with self.assertRaises(ValueError):
                    m.patch_source(s,1)

    def test_invalid_second_blob_leaves_first_untouched(self):
        with TemporaryDirectory() as root:
            base=Path(root)/m.BASE
            for rel in m.SOURCE:
                dest=base/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(HDR+"_countof(copyJobs);")
            first=base/"opticalflow/ffx_opticalflow.cpp"
            before=first.read_bytes()
            with self.assertRaisesRegex(ValueError,"git blob mismatch"):
                m.patch_files(Path(root))
            self.assertEqual(first.read_bytes(),before)

    def test_hash_determinism(self):
        self.assertEqual(m.git_blob(b"test"),"30d74d258442c7c65512eafab474568dd706c430")

if __name__=="__main__":
    unittest.main()
