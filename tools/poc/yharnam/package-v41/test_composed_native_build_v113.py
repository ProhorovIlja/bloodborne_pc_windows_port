"""V113: execute the genuine V103 -> V106 -> V111 Bash transforms together.

Offline stub Ninja tests routing, Ninja job limits and fatal exits only.
A successful result is NOT proof native game C++ or GPU libraries compile.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def load(name: str):
    src = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace('.', '_'), src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v103 = load('patch_bbnet_first_v103.py')
v106 = load('patch_bbnet_only_v106.py')
v111 = load('patch_native_ninja_jobs_v111.py')
ORIGINAL = ("case $(uname -s) in\nMINGW*|MSYS*)\n" + v103.OLD
            + "\n        exit 1\n    fi\n    ;;\nesac\n")

STUB = r'''set -euo pipefail
uname() { printf '%s\n' MINGW64_NT-10.0; }
ninja() {
    printf '%s\n' "$*" >> calls.txt
    if [[ "$*" == *' bbnet' ]]; then
        if [[ "$SIMULATE_BBNET_FAIL" == 1 ]]; then return 7; fi
        if [[ "$SIMULATE_EMPTY_ARCHIVE" == 1 ]]; then
            : > out/gpu/libbbnet.a
        else
            printf 'stub-not-a-real-game-build' > out/gpu/libbbnet.a
        fi
    else
        if [[ "$SIMULATE_GPU_FAIL" == 1 ]]; then return 8; fi
    fi
    return 0
}
mkdir -p out/gpu
'''


def find_bash():
    if os.name != 'nt':
        return shutil.which('bash')
    candidates = [Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Git' / 'bin' / 'bash.exe']
    git = shutil.which('git')
    if git:
        directory = Path(git).parent
        candidates += [directory / 'bash.exe', directory.parent / 'bin' / 'bash.exe']
    return next((str(candidate) for candidate in candidates if candidate.is_file()), None)


class ComposedNativeBuildV113(unittest.TestCase):
    def test_order_and_fail_closed_guards(self):
        staged_103 = v103.transform(ORIGINAL)
        staged_106 = v106.transform(staged_103)
        staged_111 = v111.transform(staged_106)
        self.assertIn(v103.MARKER, staged_111)
        self.assertIn(v106.MARKER, staged_111)
        self.assertIn(v111.MARKER, staged_111)
        self.assertEqual(staged_111.count('ninja -j '), 2)
        self.assertLess(staged_111.index('bbnet > out/bbnet-build.log'),
                        staged_111.index('bb-probe bb-gpu-capabilities bb-play'))
        for wrong in ((v106, ORIGINAL), (v111, staged_103)):
            with self.subTest(patcher=wrong[0].__name__), self.assertRaises(ValueError):
                wrong[0].transform(wrong[1])

    def test_actual_composed_bash_routes_and_compiler_failures(self):
        bash = find_bash()
        if bash is None:
            self.skipTest('Real Bash unavailable, never fall back to Windows WSL shim')
        staged = v111.transform(v106.transform(v103.transform(ORIGINAL)))
        subprocess.run([bash, '-n'], input=STUB + staged,
                       text=True, capture_output=True, timeout=15, check=True)
        cases = (
            ('bbnet-only', '1', '0', '0', '0', 0, False),
            ('empty-archive', '1', '0', '1', '0', 1, False),
            ('game-compile-fails', '1', '1', '0', '0', 1, False),
            ('full-native-build', '0', '0', '0', '0', 0, True),
            ('gpu-compile-fails', '0', '0', '0', '1', 1, True),
        )
        for name, only, bb_fail, empty, gpu_fail, code, gpu in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                env = os.environ.copy()
                env.update(SHYT_BBNET_ONLY=only, SIMULATE_BBNET_FAIL=bb_fail,
                           SIMULATE_EMPTY_ARCHIVE=empty, SIMULATE_GPU_FAIL=gpu_fail)
                result = subprocess.run([bash, '-c', STUB + staged], cwd=directory,
                                        env=env, text=True, capture_output=True,
                                        timeout=15, check=False)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                calls = Path(directory, 'calls.txt').read_text(encoding='utf-8').splitlines()
                self.assertEqual(calls, [
                    '-j 2 -C out/gpu bbnet',
                    *(['-j 2 -C out/gpu bb-probe bb-gpu-capabilities bb-play'] if gpu else []),
                ])
                self.assertEqual('SHYT_V106_REAL_NATIVE_BBNET_ONLY_COMPILED' in result.stdout,
                                 only == '1' and code == 0)
                if empty == '1':
                    self.assertIn('V106 original native bbnet archive missing', result.stderr)


if __name__ == '__main__':
    unittest.main()
