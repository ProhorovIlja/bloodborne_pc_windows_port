"""V123 actual CMake -P test: correct dirty build ID, no Git/jj, fail closed."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "shyt_revision_v123", Path(__file__).with_name("patch_native_ci_revision_v123.py")
)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

FIXTURE = r"""set(revision "")
set(dirty FALSE)
execute_process(COMMAND git rev-parse HEAD OUTPUT_VARIABLE revision)
execute_process(COMMAND git status --porcelain OUTPUT_VARIABLE changes)
execute_process(COMMAND @JJ@ log OUTPUT_VARIABLE jj)
set(content "#pragma once\n#define BB_SCM_REV \"@REV@\"\n")
""".replace("@JJ@", "$"+"{jj}").replace("@REV@", "$"+"{revision}")


class V123ActualNativePinnedRevision(unittest.TestCase):
    def test_original_source_guard_and_reapplication(self):
        result = v.transform(FIXTURE)
        self.assertEqual(result.count(v.MARKER), 1)
        self.assertIn("execute_process(COMMAND git status --porcelain", result)
        with self.assertRaisesRegex(ValueError, "already transformed"):
            v.transform(result)
        for changed in (
            FIXTURE.replace("set(dirty FALSE)", "set(dirty TRUE)"),
            FIXTURE.replace("git status --porcelain", "git status --short"),
        ):
            with self.subTest(changed=changed[:40]), self.assertRaises(ValueError):
                v.transform(changed)

    def test_real_cmake_mode_does_not_call_git_and_preserves_existing_header(self):
        if not shutil.which("cmake"):
            self.skipTest("CMake needed to test real interpreter")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            script = root / "revision.cmake"
            output = root / "bbcoop_revision.h"
            script.write_text(v.transform(FIXTURE), encoding="utf-8")
            env = os.environ.copy()
            env["SHYT_BBCOOP_CI_PINNED_REVISION"] = v.PIN + "-dirty"
            cmd = ["cmake", "-DOUT=" + str(output), "-DSOURCE=" + d, "-P", str(script)]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("SHYT_V123_BBCOOP_REVISION_GIT_FREE_PASS", result.stdout)
            self.assertEqual(output.read_text(),
                             '#pragma once\n#define BB_SCM_REV "' + v.PIN + '-dirty"\n')
            before = output.stat().st_mtime_ns
            same = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(same.returncode, 0, same.stdout + same.stderr)
            self.assertEqual(output.stat().st_mtime_ns, before)
            env["SHYT_BBCOOP_CI_PINNED_REVISION"] = "wrong-sha-dirty"
            bad = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("SHYT_V123_WRONG_PINNED_DIRTY_REVISION", bad.stderr)
            self.assertEqual(output.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
