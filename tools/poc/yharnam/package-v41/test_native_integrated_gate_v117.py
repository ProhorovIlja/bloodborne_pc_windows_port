"""V117 test: source-exact integrated archive gate before GPU; NOT a game compile."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

FILE = Path(__file__).with_name("patch_native_integrated_gate_v117.py")
spec = importlib.util.spec_from_file_location("v117_integrated", FILE)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

FIXTURE = """case $(uname -s) in
MINGW*|MSYS*)
    # SHYT-V103-NATIVE-BBNET-FIRST
    # SHYT-V111-NINJA-BOUNDED-COMPILE
    # SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG
    # SHYT-V116-NATIVE-LEAN-DWARF
    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    # SHYT-V106-BBNET-ONLY: opt in
    if [[ "$SHYT_BBNET_ONLY" == 1 ]]; then exit 0; fi
    if ! ninja -j 2 -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then
      exit 1
    fi
    ;;
esac
"""
HARNESS = r"""set -euo pipefail
uname() { echo MINGW64_NT-10.0; }
python() {
  printf '%s\n' "$*" >> verify.calls
  if [[ "$FAIL_PROVENANCE" == "1" ]]; then return 9; fi
}
ninja() { echo gpu >> gpu.calls; return 0; }
mkdir -p out/gpu
"""


def bash_executable():
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    candidates = [Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                  / "Git" / "bin" / "bash.exe"]
    if git:
        loc = Path(git).parent
        candidates += [loc / "bash.exe", loc.parent / "bin" / "bash.exe"]
    return next((str(p) for p in candidates if p.is_file()), None)


class V117Audit(unittest.TestCase):
    def test_exact_source_and_compile_order(self):
        patched = v.transform(FIXTURE)
        self.assertEqual(patched.count(v.MARKER), 1)
        self.assertLess(patched.index("verify_bbnet_archive_v108.py"),
                        patched.index("bb-probe bb-gpu-capabilities bb-play"))
        self.assertIn("SHYT_V117_ORIGINAL_GAME_CXX_ARCHIVE_VERIFIED_BEFORE_GPU", patched)
        with self.assertRaisesRegex(ValueError, "already integrated"):
            v.transform(patched)
        for broken in (
            FIXTURE.replace("SHYT-V116-NATIVE-LEAN-DWARF", "removed"),
            FIXTURE.replace("SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED", "wrong-target"),
            FIXTURE.replace("MINGW*|MSYS*)", "unknown*)"),
            FIXTURE + FIXTURE,
        ):
            with self.subTest(broken=broken[:48]), self.assertRaises(ValueError):
                v.transform(broken)

    def test_actual_bash_success_failure_and_opt_out(self):
        bash = bash_executable()
        if bash is None:
            self.skipTest("True Bash missing; never execute Windows WSL shim")
        code = HARNESS + v.transform(FIXTURE)
        syntax = subprocess.run([bash, "-n"], input=code, text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        cases = (
            ("1", "0", "0", True, True, True),
            ("1", "1", "0", False, True, False),
            ("0", "1", "0", True, False, True),
            ("1", "0", "1", True, True, False),
        )
        for gate, fail, bbnet_only, ok, called, gpu in cases:
            with self.subTest(gate=gate, fail=fail, bbnet_only=bbnet_only), \
                 tempfile.TemporaryDirectory() as directory:
                env = os.environ.copy()
                env.update(SHYT_V117_VERIFY_AFTER_BBNET=gate, FAIL_PROVENANCE=fail,
                           SHYT_BBNET_ONLY=bbnet_only)
                result = subprocess.run([bash, "-c", code], cwd=directory, env=env,
                                        text=True, capture_output=True, timeout=15)
                self.assertEqual(result.returncode == 0, ok, result.stderr)
                self.assertEqual((Path(directory)/"verify.calls").exists(), called)
                self.assertEqual((Path(directory)/"gpu.calls").exists(), gpu)
                self.assertEqual("SHYT_V117_ORIGINAL_GAME_CXX_ARCHIVE_VERIFIED_BEFORE_GPU" in result.stdout,
                                 called and fail == "0")


if __name__ == "__main__":
    unittest.main()
