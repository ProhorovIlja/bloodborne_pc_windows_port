"""V119 original CMake Windows-native revision target fail-closed checks."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import time
import unittest

f = Path(__file__).with_name("stage_windows_revision_v119.py")
spec = importlib.util.spec_from_file_location("yt130_v119_scm_hotpath", f)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalWindowsRevision(unittest.TestCase):
    @staticmethod
    def fixture():
        return (
            'set(revision "")\n'
            'execute_process(COMMAND jj log)\n'
            'execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY "SOURCE")\n'
            'execute_process(COMMAND git status --porcelain --untracked-files=no)\n'
            'if (NOT previous STREQUAL content)\n'
            '  file(WRITE "OUT" "content")\n'
            'endif()\n'
        )

    def test_staged_exact_revision_is_truthful_source_pinned_and_no_child_scm(self):
        changed = m.rewrite(self.fixture())
        self.assertIn(m.MARK, changed)
        self.assertIn(m.PIN + "-dirty", changed)
        self.assertIn("BB_SCM_REV", changed)
        self.assertNotIn("execute_process(", changed)
        self.assertIn("if (NOT previous STREQUAL content)", changed)
        self.assertIn('if (NOT DEFINED OUT OR OUT STREQUAL "")', changed)
        self.assertEqual(m.BLOB, "9b8aec040f81ef1a65f838065ad46de87046f040")

    def test_double_stage_or_drift_is_refused(self):
        original = self.fixture()
        with self.assertRaisesRegex(ValueError, "source drift"):
            m.rewrite(m.rewrite(original))
        for old in (
            "execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY",
            "execute_process(COMMAND git status --porcelain --untracked-files=no",
            "if (NOT previous STREQUAL content)",
        ):
            with self.subTest(old=old):
                with self.assertRaisesRegex(ValueError, "source drift"):
                    m.rewrite(original.replace(old, "BROKEN"))

    def test_real_cmake_compiles_and_preserves_header_timestamp(self):
        # Execute the actual CMake script, not a simulated Python expansion.
        cmake = __import__("shutil").which("cmake")
        if cmake is None:
            self.skipTest("cmake not installed; Windows preflight also checks")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root / "revision.cmake"
            header = root / "bbcoop_revision.h"
            script.write_text(m.rewrite(self.fixture()), encoding="utf-8")
            command = [cmake, f"-DOUT={header}", f"-DSOURCE={root}", "-P", str(script)]
            subprocess.run(command, check=True, timeout=8, capture_output=True, text=True)
            expected = '#pragma once\n#define BB_SCM_REV "' + m.PIN + '-dirty"\n'
            self.assertEqual(header.read_text(encoding="utf-8"), expected)
            before = header.stat().st_mtime_ns
            # A no-op build must NOT change the output timestamp and cause
            # downstream recompiles of every game/shadnet translation unit.
            time.sleep(0.012)
            subprocess.run(command, check=True, timeout=8, capture_output=True, text=True)
            self.assertEqual(header.read_text(encoding="utf-8"), expected)
            self.assertEqual(header.stat().st_mtime_ns, before)
            script_without_out = [cmake, "-P", str(script)]
            bad = subprocess.run(script_without_out, timeout=8, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)

if __name__ == "__main__":
    unittest.main()
