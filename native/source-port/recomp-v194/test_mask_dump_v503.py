# SPDX-License-Identifier: GPL-2.0-or-later
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'linux', 'Linux mount namespaces required')
class TestMaskedBoot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.dump = self.root / 'original dump'
        self.dump.mkdir()
        self.original = self.dump / 'eboot.bin'
        self.original.write_bytes(b'synthetic original')
        self.asset = self.root / 'asset.dcx'
        self.asset.write_bytes(b'synthetic asset')
        self.alias = self.root / 'alias'
        self.alias.symlink_to(self.dump, target_is_directory=True)
        self.mask = Path(__file__).with_name('mask_dump_v502.sh').resolve()
        self.python = str(Path(sys.executable).resolve())

    def run_host(self, source, *, masked=False, cwd=None, env=None):
        cmd = [self.python, '-I', '-c', source, str(self.original),
               str(self.alias / 'eboot.bin'), str(self.asset)]
        if masked:
            cmd = ['bash', str(self.mask), str(self.dump), '--', *cmd]
        return subprocess.run(cmd, cwd=cwd or self.root, env=env, text=True,
                              capture_output=True, timeout=10)

    def test_original_dependent_baseline_fails_when_masked(self):
        source = 'import sys; from pathlib import Path; print(Path(sys.argv[1]).read_bytes())'
        baseline = self.run_host(source)
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        self.assertIn('synthetic original', baseline.stdout)
        masked = self.run_host(source, masked=True)
        self.assertNotEqual(masked.returncode, 0)
        self.assertIn('dump masked', masked.stderr)
        self.assertIn('FileNotFoundError', masked.stderr)
        self.assertEqual(self.original.read_bytes(), b'synthetic original')

    def test_assets_only_host_and_readonly_mount(self):
        source = '''import errno, sys
from pathlib import Path
original, alias, asset = map(Path, sys.argv[1:])
assert not original.exists() and not alias.exists()
assert asset.read_bytes() == b'synthetic asset'
try:
    original.write_bytes(b'changed')
except OSError as e:
    assert e.errno == errno.EROFS, e
else:
    raise AssertionError('dump mount writable')
raise SystemExit(27)
'''
        result = self.run_host(source, masked=True)
        self.assertEqual(result.returncode, 27, result.stderr)
        self.assertIn('dump masked', result.stderr)
        self.assertEqual(self.original.read_bytes(), b'synthetic original')

    def test_refuses_workdir_and_tempdir_inside_dump(self):
        source = 'print("unexpected host execution")'
        for kwargs in ({'cwd': self.dump}, {'env': {**os.environ, 'TMPDIR': str(self.dump)}}):
            with self.subTest(kwargs=tuple(kwargs)):
                result = self.run_host(source, masked=True, **kwargs)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('unexpected host execution', result.stdout)
                self.assertEqual(list(self.dump.iterdir()), [self.original])


if __name__ == '__main__':
    unittest.main()
