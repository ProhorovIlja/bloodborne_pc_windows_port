"""Offline fixture tests; no actual game, proprietary binaries, network or installs."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

PATH = Path(__file__).with_name('native_package_integrity_v185.py')
SPEC = importlib.util.spec_from_file_location('native_v185', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def fake_pe() -> bytes:
    b = bytearray(512)
    b[:2] = b'MZ'
    struct.pack_into('<I', b, 0x3c, 0x80)
    b[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', b, 0x84, 0x8664)
    return bytes(b)


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'client'
        self.root.mkdir()
        self.data = {p: fake_pe() for p in audit.REQUIRED_PE}
        self.data.update({'run.py': b'# harmless fixture\n',
                          'VERSION.txt': b'Bloodborne PC native Windows test build',
                          'bin/fsr24/sdk.dll': b'SDK-only runtime, no game',
                          'bin/reshade/README.txt': b'Nested optional runtime'})
        self.zip = Path(self.tmp.name) / 'source.zip'

    def write_dir(self):
        for name, value in self.data.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(value)

    def write_zip(self, malicious=None):
        with zipfile.ZipFile(self.zip, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, data in self.data.items():
                z.writestr('BBSC-RELEASE/' + name, data)
            if malicious:
                for name, data in malicious:
                    z.writestr(name, data)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = audit.main([str(args[0]), *map(str, args[1:])])
        return code, out.getvalue(), err.getvalue()

    def test_zip_and_directory_same_reproducible_fingerprint(self):
        self.write_zip()
        self.write_dir()
        a = audit.inspect(self.zip)
        b = audit.inspect(self.root)
        self.assertEqual(a, b)
        self.assertEqual(a['summary']['pe_amd64_verified'], 4)
        self.assertEqual(a['summary']['nested_bin_count'], 2)
        self.assertFalse(a['summary']['gameplay_boot_tested'])
        self.assertLess(len(json.dumps(a['summary']).encode()), 16384)

    def test_private_manifest_detects_modified_and_missing_nested_runtime(self):
        self.write_dir()
        manifest = Path(self.tmp.name) / 'private-manifest.json'
        code, out, err = self.cli(self.root, '--write-manifest', manifest)
        self.assertEqual(code, 0, err)
        self.assertTrue(manifest.exists())
        self.assertNotIn('bin/fsr24/sdk.dll', out)
        self.assertEqual(self.cli(self.root, '--verify-manifest', manifest)[0], 0)
        (self.root / 'bin/fsr24/sdk.dll').write_bytes(b'changed')
        status, out, err = self.cli(self.root, '--verify-manifest', manifest)
        self.assertEqual(status, 2)
        self.assertEqual(out, '')
        self.assertNotIn('bin/fsr24/sdk.dll', err)
        (self.root / 'bin/fsr24/sdk.dll').unlink()
        self.assertEqual(self.cli(self.root, '--verify-manifest', manifest)[0], 2)

    def test_required_pe_not_just_name(self):
        self.data['bin/bb-probe.exe'] = b'not PE'
        self.write_zip()
        code, out, err = self.cli(self.zip)
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertIn('not Windows x86-64 PE', err)
        self.data.pop('bin/bb-probe.exe')
        self.write_zip()
        self.assertIn('required native runtime component missing', self.cli(self.zip)[2])

    def test_reject_zip_slip_duplicates_and_retail_game_content(self):
        for malicious in [[('../steal', b'private')],
                          [('BBSC-RELEASE/BIN/BB-PROBE.exe', b'fake')],
                          [('BBSC-RELEASE/game/CUSA03173/eboot.bin', b'game')]]:
            with self.subTest(malicious=malicious[0][0]):
                self.write_zip(malicious)
                code, out, err = self.cli(self.zip)
                self.assertEqual(code, 2)
                self.assertEqual(out, '')
        self.data['bin/../escapes.txt'] = b'a'
        self.write_zip()
        self.assertEqual(self.cli(self.zip)[0], 2)

    def test_directory_symlink_rejected(self):
        self.write_dir()
        p = self.root / 'bin' / 'linked.dll'
        try:
            p.symlink_to(self.root / 'run.py')
        except (OSError, NotImplementedError):
            self.skipTest('Windows symlink privilege unavailable')
        self.assertEqual(self.cli(self.root)[0], 2)

    def test_never_write_manifests_into_runtime_or_print_user_paths(self):
        self.write_dir()
        code, out, err = self.cli(self.root, '--write-manifest', self.root / 'private.json')
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertFalse((self.root / 'private.json').exists())
        self.assertNotIn(str(self.root), err)
        self.assertNotIn('PRIVATE', err)


if __name__ == '__main__':
    unittest.main()
