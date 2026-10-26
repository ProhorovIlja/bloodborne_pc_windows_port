"""V116 keep release-grade -O2 while shrinking Windows Clang64 CI DWARF."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), HERE / name
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v115 = load("patch_native_cmake_trace_v115.py")
v116 = load("patch_native_lean_dwarf_v116.py")
CONFIGURE = v115.PATCHED.replace(
    "-DCMAKE_CXX_COMPILER=clang++ > out/cmake-configure.log 2>&1; then",
    "-DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER_LAUNCHER=ccache "
    "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache > out/cmake-configure.log 2>&1; then",
)
FIXTURE = (
    "case $(uname -s) in\nMINGW*|MSYS*)\n"
    "    # SHYT-V111-NINJA-BOUNDED-COMPILE\n"
    + CONFIGURE + "\n    ;;\nesac\n"
)


def find_bash():
    if os.name != "nt":
        return shutil.which("bash")
    candidates = [Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                  / "Git" / "bin" / "bash.exe"]
    git = shutil.which("git")
    if git:
        d = Path(git).parent
        candidates += [d / "bash.exe", d.parent / "bin" / "bash.exe"]
    return next((str(c) for c in candidates if c.is_file()), None)


class NativeLeanDwarfV116(unittest.TestCase):
    def test_exact_source_and_single_configure_override(self):
        actual = v116.transform(FIXTURE)
        self.assertEqual(actual.count(v116.MARKER), 1)
        self.assertEqual(actual.count("gline-tables-only"), 2)
        self.assertIn('-DCMAKE_C_FLAGS_RELWITHDEBINFO="-O2 -gline-tables-only -DNDEBUG"', actual)
        self.assertIn('-DCMAKE_CXX_FLAGS_RELWITHDEBINFO="-O2 -gline-tables-only -DNDEBUG"', actual)
        self.assertIn("-DCMAKE_CXX_COMPILER_LAUNCHER=ccache", actual)
        self.assertIn("> out/cmake-configure.log 2>&1", actual)
        self.assertIn("SHYT_V115_NATIVE_CMAKE_CONFIGURE_FAILED", actual)
        with self.assertRaisesRegex(ValueError, "already applied"):
            v116.transform(actual)
        for damaged in (
            FIXTURE.replace("MINGW*|MSYS*)", "OTHER*)"),
            FIXTURE.replace("CMAKE_BUILD_TYPE=RelWithDebInfo", "CMAKE_BUILD_TYPE=Debug"),
            FIXTURE.replace("CXX_COMPILER_LAUNCHER=ccache", "CXX_COMPILER_LAUNCHER=none"),
            FIXTURE + FIXTURE,
        ):
            with self.subTest(damaged=damaged[:48]), self.assertRaises(ValueError):
                v116.transform(damaged)

    def test_windows_compose_bash_invocation_keeps_optimization(self):
        bash = find_bash()
        if not bash:
            self.skipTest("Real non-WSL Git Bash not installed")
        script = v116.transform(FIXTURE)
        header = r"""set -euo pipefail
uname() { echo MINGW64_NT-10.0; }
cmake() {
    printf '%s\n' "$@" > cmake.args
    echo "CMAKE_DIAGNOSTIC_PRESERVED"
}
"""
        check = subprocess.run([bash, "-n"], input=header + script,
                               capture_output=True, text=True, timeout=15)
        self.assertEqual(check.returncode, 0, check.stderr)
        with tempfile.TemporaryDirectory() as temp:
            run = subprocess.run([bash, "-c", header + script], cwd=temp,
                                 capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            args = Path(temp, "cmake.args").read_text(encoding="utf-8").splitlines()
            self.assertIn("-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O2 -gline-tables-only -DNDEBUG", args)
            self.assertIn("-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2 -gline-tables-only -DNDEBUG", args)
            self.assertIn("-DCMAKE_CXX_COMPILER_LAUNCHER=ccache", args)
            self.assertIn("-DCMAKE_BUILD_TYPE=RelWithDebInfo", args)
            self.assertIn("CMAKE_DIAGNOSTIC_PRESERVED",
                          Path(temp, "out/cmake-configure.log").read_text())


if __name__ == "__main__":
    unittest.main()
