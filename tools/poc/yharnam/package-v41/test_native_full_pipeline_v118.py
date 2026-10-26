"""V118: compose the WHOLE pinned Windows Bash pipeline, not isolated patches.

V103 -> V106 -> V111 -> ccache -> V115 -> V116 -> V117.
A scripted fake CMake/Ninja/verifier checks real Bash parsing and phase order.
It cannot prove the genuine C++ code is compilable.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent

def module(name):
    p = ROOT / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

a = module("patch_bbnet_first_v103.py")
b = module("patch_bbnet_only_v106.py")
c = module("patch_native_ninja_jobs_v111.py")
d = module("patch_native_cmake_trace_v115.py")
e = module("patch_native_lean_dwarf_v116.py")
f = module("patch_native_integrated_gate_v117.py")

CCACHE = " -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
ORIGINAL_CMAKE = d.ORIGINAL.split('\n    echo "GPU library')[0].replace(CCACHE, "")
ORIGINAL_SCRIPT = (
    "case $(uname -s) in\nMINGW*|MSYS*)\n"
    + ORIGINAL_CMAKE + "\n" + a.OLD
    + "\n      exit 1\n    fi\n    ;;\nesac\n"
)
HARNESS = r"""set -euo pipefail
uname() { echo MINGW64_NT-10.0; }
cmake() { printf '%s\n' "$@" > cmake.args; echo CMAKE_ACCEPTED; }
ninja() {
    echo "$*" >> ninja.calls
    if [[ "$*" == *' bbnet' ]]; then
        mkdir -p out/gpu
        printf 'fake-game-library-for-control-flow-only' > out/gpu/libbbnet.a
    fi
}
python() {
    echo "$*" >> validator.calls
    if [[ "$FAIL_VERIFICATION" == 1 ]]; then return 10; fi
}
mkdir -p out/gpu
"""


def compose():
    first = a.transform(ORIGINAL_SCRIPT)
    second = b.transform(first)
    third = c.transform(second)
    old = "-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ >/dev/null"
    new = "-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++" + CCACHE + " >/dev/null"
    if third.count(old) != 1:
        raise ValueError("ccache injection source no longer unique")
    fourth = third.replace(old, new, 1)
    return f.transform(e.transform(d.transform(fourth)))


def real_bash():
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    candidates = [Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                  / "Git" / "bin" / "bash.exe"]
    if git:
        directory = Path(git).parent
        candidates.extend((directory / "bash.exe", directory.parent / "bin" / "bash.exe"))
    return next((str(p) for p in candidates if p.is_file()), None)


class NativeWholePipelineV118(unittest.TestCase):
    def test_all_patches_compose_source_exactly_once(self):
        built = compose()
        for marker in (a.MARKER, b.MARKER, c.MARKER, d.MARKER, e.MARKER, f.MARKER):
            self.assertEqual(built.count(marker), 1, marker)
        self.assertIn("CMAKE_CXX_COMPILER_LAUNCHER=ccache", built)
        self.assertEqual(built.count("gline-tables-only"), 2)
        self.assertEqual(built.count('ninja -j "'), 2)
        self.assertLess(built.index("out/bbnet-build.log"),
                        built.index("verify_bbnet_archive_v108.py"))
        self.assertLess(built.index("verify_bbnet_archive_v108.py"),
                        built.index("bb-probe bb-gpu-capabilities bb-play"))
        with self.assertRaisesRegex(ValueError, "source differs"):
            f.transform(ORIGINAL_SCRIPT)

    def test_composed_original_windows_bash_routes_and_failure(self):
        bash = real_bash()
        if not bash:
            self.skipTest("Non-WSL Bash unavailable")
        program = HARNESS + compose()
        syntax = subprocess.run([bash, "-n"], input=program, text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        for only, fail, ok, gpu in (
            ("1", "0", True, False),
            ("0", "0", True, True),
            ("0", "1", False, False),
        ):
            with self.subTest(only=only, fail=fail), tempfile.TemporaryDirectory() as tmp:
                env = os.environ.copy()
                env.update(SHYT_BBNET_ONLY=only, SHYT_V117_VERIFY_AFTER_BBNET="1",
                           FAIL_VERIFICATION=fail)
                proc = subprocess.run([bash, "-c", program], cwd=tmp,
                                      env=env, text=True, capture_output=True, timeout=15)
                self.assertEqual(proc.returncode == 0, ok, proc.stdout + proc.stderr)
                args = (Path(tmp)/"cmake.args").read_text(encoding="utf-8")
                self.assertIn("-DCMAKE_CXX_COMPILER_LAUNCHER=ccache", args)
                self.assertIn("-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2 -gline-tables-only -DNDEBUG", args)
                ninja = (Path(tmp)/"ninja.calls").read_text(encoding="utf-8")
                self.assertIn("-j 2 -C out/gpu bbnet", ninja)
                self.assertEqual("bb-probe bb-gpu-capabilities bb-play" in ninja, gpu)
                self.assertTrue((Path(tmp)/"validator.calls").exists())


if __name__ == "__main__":
    unittest.main()
