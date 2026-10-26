"""V106 exact original game bbnet-only build branch + default full build."""
import importlib.util
from pathlib import Path
import unittest
script=Path(__file__).with_name("patch_bbnet_only_v106.py")
spec=importlib.util.spec_from_file_location("shyt_bbnet_v106",script)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
FIXTURE="""case $(uname -s) in
MINGW*|MSYS*)
    # SHYT-V103-NATIVE-BBNET-FIRST
    if ! ninja -C out/gpu bbnet > out/bbnet-build.log 2>&1; then
        exit 1
    fi
    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then
        exit 1
    fi
esac
"""
class TestBbnetOnlyV106(unittest.TestCase):
    def test_original_cpp_archive_without_gpu_and_default_unchanged(self):
        out=v.transform(FIXTURE)
        self.assertIn(v.MARKER,out)
        self.assertIn("if [[ ${SHYT_BBNET_ONLY:-0} == 1 ]]; then",out)
        self.assertIn("test -s out/gpu/libbbnet.a",out)
        self.assertIn("SHYT_V106_REAL_NATIVE_BBNET_ONLY_COMPILED",out)
        self.assertEqual(out.count("if ! ninja -C out/gpu bbnet"),1)
        self.assertEqual(out.count("if ! ninja -C out/gpu bb-probe"),1)
        self.assertLess(out.index("test -s out/gpu/libbbnet.a"),out.index("if ! ninja -C out/gpu bb-probe"))
        self.assertIn("exit 0\n    fi\n    if ! ninja -C out/gpu bb-probe",out)
        with self.assertRaisesRegex(ValueError,"already added"): v.transform(out)
    def test_wrong_original_builder_rejected(self):
        for bad in (FIXTURE.replace("SHYT-V103-NATIVE-BBNET-FIRST","different game"),
                    FIXTURE.replace("MINGW*|MSYS*)","OTHER*)"),
                    FIXTURE.replace("bb-probe","something_else"),FIXTURE+FIXTURE):
            with self.subTest(change=bad[:55]), self.assertRaises(ValueError): v.transform(bad)
if __name__=="__main__": unittest.main()
