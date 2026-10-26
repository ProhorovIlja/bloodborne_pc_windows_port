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

    def test_runtime_bbnet_only_and_default_routes(self):
        """Execute the actual patched Bash branch with stubbed Ninja, not just string matching.

        This only tests control flow; the Windows workflow must still compile
        genuine C++ into libbbnet.a before declaring its own success.
        """
        import os
        import shutil
        import subprocess
        import tempfile
        if shutil.which("bash") is None:
            self.skipTest("Bash unavailable; original source checks still run")
        prefix = r"""set -euo pipefail
uname() { printf '%s\n' 'MINGW64_NT-10.0'; }
ninja() {
    printf '%s\n' "$*" >> calls.txt
    case "$*" in
        "-C out/gpu bbnet")
            if [[ "$SIMULATE_BBNET_FAIL" == "1" ]]; then return 7; fi
            if [[ "$SIMULATE_EMPTY_ARCHIVE" == "1" ]]; then
                : > out/gpu/libbbnet.a
            else
                printf 'test-nonempty-archive' > out/gpu/libbbnet.a
            fi
            ;;
    esac
    return 0
}
mkdir -p out/gpu
"""
        script = prefix + v.transform(FIXTURE)
        scenarios = (
            # name, opt-in, compile-fails, empty-archive, exit, GPU-invoked
            ("only-success", "1", "0", "0", 0, False),
            ("only-empty-archive", "1", "0", "1", 1, False),
            ("only-compile-fails", "1", "1", "0", 1, False),
            ("default-full-route", "0", "0", "0", 0, True),
        )
        for name, opt_in, fails, empty, exit_code, gpu_expected in scenarios:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                env = os.environ.copy()
                env.update(SHYT_BBNET_ONLY=opt_in,
                           SIMULATE_BBNET_FAIL=fails,
                           SIMULATE_EMPTY_ARCHIVE=empty)
                run = subprocess.run(
                    ["bash", "-c", script], cwd=d, env=env,
                    text=True, capture_output=True, timeout=15, check=False)
                self.assertEqual(run.returncode, exit_code, run.stdout + run.stderr)
                calls = Path(d, "calls.txt").read_text(encoding="utf-8").splitlines()
                self.assertTrue(calls and calls[0] == "-C out/gpu bbnet", calls)
                self.assertEqual(any("bb-probe bb-gpu-capabilities bb-play" in c
                                     for c in calls), gpu_expected, calls)
                self.assertEqual(
                    "SHYT_V106_REAL_NATIVE_BBNET_ONLY_COMPILED" in run.stdout,
                    bool(opt_in == "1" and exit_code == 0),
                )
                if empty == "1":
                    self.assertIn("V106 original native bbnet archive missing", run.stderr)

if __name__=="__main__": unittest.main()
