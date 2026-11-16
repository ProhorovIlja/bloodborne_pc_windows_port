# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from audit_bundle_v500 import audit


class TestPreparedBundle(unittest.TestCase):
    def test_renamed_guest_payloads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(2, 6):
                (root / f'image{i}.dat').write_bytes(f'BBPROBE{i}'.encode() + bytes(24))
            (root / 'asset.dcx').write_bytes(b'DCX\0')
            (root / 'host.elf').write_bytes(b'\x7fELF\x02\x01' + bytes(10) + b'\x03\x00\x3e\x00')
            result = audit(root)
            self.assertEqual(result['findings'], [(f'image{i}.dat', 'bbport-guest-image') for i in range(2, 6)])
            self.assertEqual(result['files_inspected'], 6)
            self.assertFalse(result['runtime_verified'])

    def test_root_and_nested_links(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bundle').mkdir()
            (root / 'outside').mkdir()
            (root / 'outside' / 'private').write_bytes(b'BBPROBE5')
            link = root / 'bundle' / 'indirect'
            try:
                link.symlink_to(root / 'outside', target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks unavailable')
            with self.assertRaises(ValueError):
                audit(link)
            self.assertEqual(audit(root / 'bundle')['findings'], [('indirect', 'link-or-reparse-point')])

    def test_cli_distinguishes_clean_refused_and_flagged(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cmd = [sys.executable, str(Path(__file__).with_name('audit_bundle_v500.py')), str(root)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            (root / 'asset.dat').write_bytes(b'ordinary data')
            clean = subprocess.run(cmd, capture_output=True)
            self.assertEqual(clean.returncode, 0)
            self.assertFalse(json.loads(clean.stdout)['runtime_verified'])
            (root / 'renamed.dat').write_bytes(b'BBPROBE5')
            flagged = subprocess.run(cmd, capture_output=True)
            self.assertEqual(flagged.returncode, 3)
            self.assertEqual(json.loads(flagged.stdout)['findings'], [['renamed.dat', 'bbport-guest-image']])
