"""V103 source-pinned native game-before-GPU compile tests."""
import importlib.util
from pathlib import Path
import unittest

source=Path(__file__).with_name("patch_bbnet_first_v103.py")
spec=importlib.util.spec_from_file_location("v103",source)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

ORIGINAL='''#!/usr/bin/env bash
set -euo pipefail
case $(uname -s) in
MINGW*|MSYS*)
    echo "GPU library and loader: LTO ${BB_LTO:-OFF}"
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then
       echo Failed
    fi
esac
'''
class NativeGameFirstV103Tests(unittest.TestCase):
    def test_bbnet_compiled_before_bbgpu_and_failure_is_fail_closed(self):
        transformed=v.transform(ORIGINAL)
        self.assertIn(v.MARKER,transformed)
        self.assertLess(transformed.index("ninja -C out/gpu bbnet"),
                        transformed.index("ninja -C out/gpu bb-probe"))
        self.assertIn("out/bbnet-build.log",transformed)
        self.assertIn("exit 1",transformed)
        self.assertIn("SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED",transformed)
        self.assertEqual(transformed.count("ninja -C out/gpu bbnet"),1)
        with self.assertRaisesRegex(ValueError,"already applied"):
            v.transform(transformed)
    def test_source_drift_must_not_be_silently_applied(self):
        for bad in [ORIGINAL.replace("bb-play","bb-something"),
                    ORIGINAL.replace("MINGW*|MSYS*)","UNIX*)"),
                    ORIGINAL+ORIGINAL]:
            with self.subTest(case=bad[:65]),self.assertRaisesRegex(ValueError,"unexpected"):
                v.transform(bad)

if __name__=="__main__":
    unittest.main()
