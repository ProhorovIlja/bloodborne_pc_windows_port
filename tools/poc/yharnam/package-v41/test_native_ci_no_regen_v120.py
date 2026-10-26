"""Real offline CMake/Ninja proof: static CI configure drops glob rechecks.

The immutable pinned checkout has all source patches applied BEFORE CMake.
This does not claim any Bloodborne C++ build has passed.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

class FrozenWindowsNativeCI(unittest.TestCase):
    def test_real_cpp_build_and_suppressed_verify_globs(self):
        if not shutil.which("cmake") or not shutil.which("ninja"):
            self.skipTest("Need CMake and Ninja available on PATH for runtime smoke")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "main.cpp").write_text("int main(){return 0;}\n")
            source = (
                "cmake_minimum_required(VERSION 3.24)\n"
                "project(shyt_v120 LANGUAGES CXX)\n"
                "file(GLOB SOURCES CONFIGURE_DEPENDS src/*.cpp)\n"
                "add_executable(shyt_v120 @SOURCE_VAR@)\n"
            ).replace("@SOURCE_VAR@", "$" + "{SOURCES}")
            (root / "CMakeLists.txt").write_text(source)
            for mode, suppress in [("normal", False), ("ci_frozen", True)]:
                build = root / mode
                args = ["cmake", "-S", str(root), "-B", str(build), "-G", "Ninja"]
                if suppress:
                    args.append("-DCMAKE_SUPPRESS_REGENERATION=ON")
                conf = subprocess.run(args, capture_output=True, text=True, timeout=60)
                self.assertEqual(conf.returncode, 0, conf.stdout + conf.stderr)
                ninja_file = (build / "build.ninja").read_text()
                self.assertEqual("VERIFY_GLOBS" in ninja_file, not suppress)
                run = subprocess.run(
                    ["ninja", "-C", str(build), "shyt_v120"],
                    capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertTrue((build / "shyt_v120").exists()
                                or (build / "shyt_v120.exe").exists())

if __name__ == "__main__":
    unittest.main()
