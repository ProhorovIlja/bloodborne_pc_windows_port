"""V115 reject hidden CMake configuration output and preserve failure evidence."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "v115_native_cmake", here / "patch_native_cmake_trace_v115.py"
)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

fixture = (
    "case $(uname -s) in\nMINGW*|MSYS*)\n"
    "    # SHYT-V103-NATIVE-BBNET-FIRST\n"
    "    # SHYT-V111-NINJA-BOUNDED-COMPILE\n"
    + v.ORIGINAL + "\n    ;;\nesac\n"
)


class V115Source(unittest.TestCase):
    def test_only_pinned_windows_configure_replaced(self):
        transformed = v.transform(fixture)
        self.assertEqual(transformed.count(v.MARKER), 1)
        self.assertIn("> out/cmake-configure.log 2>&1", transformed)
        self.assertNotIn("clang++ >/dev/null", transformed)
        self.assertIn("SHYT_V115_NATIVE_CMAKE_CONFIGURE_PASS", transformed)
        self.assertIn("SHYT_V115_NATIVE_CMAKE_CONFIGURE_FAILED", transformed)
        self.assertIn("# SHYT-V103-NATIVE-BBNET-FIRST", transformed)
        with self.assertRaisesRegex(ValueError, "already added"):
            v.transform(transformed)

    def test_changed_windows_build_rejected(self):
        for changed in (
            fixture.replace("MINGW*|MSYS*)", "OTHER*)"),
            fixture.replace("CMAKE_CXX_COMPILER=clang++", "CMAKE_CXX_COMPILER=gcc"),
            fixture.replace("SHYT-V103-NATIVE-BBNET-FIRST", "not-pinned"),
            fixture + fixture,
        ):
            with self.subTest(changed=changed[:55]), self.assertRaises(ValueError):
                v.transform(changed)

    def test_real_bash_captures_both_success_and_failure(self):
        import os
        import shutil
        if os.name == "nt":
            git = shutil.which("git")
            candidates = [
                Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                / "Git" / "bin" / "bash.exe",
            ]
            if git:
                d = Path(git).parent
                candidates += [d / "bash.exe", d.parent / "bin" / "bash.exe"]
            bash = next((str(p) for p in candidates if p.is_file()), None)
        else:
            bash = shutil.which("bash")
        if bash is None:
            self.skipTest("real non-WSL Bash unavailable")
        code = """set -euo pipefail
cmake() {
    echo "V115_CAPTURED_CMAKE_MESSAGE"
    if [[ "$SIMULATE_CMAKE_FAIL" == 1 ]]; then return 9; fi
}
"""
        for fail in ("0", "1"):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as tmp:
                env = os.environ.copy()
                env["SIMULATE_CMAKE_FAIL"] = fail
                proc = subprocess.run(
                    [bash, "-c", code + v.PATCHED],
                    cwd=tmp, env=env, capture_output=True,
                    text=True, check=False, timeout=15,
                )
                expected_code = 0 if fail == "0" else 1
                self.assertEqual(proc.returncode, expected_code,
                                 proc.stdout + proc.stderr)
                log = Path(tmp, "out/cmake-configure.log").read_text(encoding="utf-8")
                self.assertIn("V115_CAPTURED_CMAKE_MESSAGE", log)
                self.assertEqual(
                    "SHYT_V115_NATIVE_CMAKE_CONFIGURE_PASS" in proc.stdout,
                    fail == "0",
                )
                self.assertEqual(
                    "SHYT_V115_NATIVE_CMAKE_CONFIGURE_FAILED" in proc.stderr,
                    fail == "1",
                )


if __name__ == "__main__":
    unittest.main()
