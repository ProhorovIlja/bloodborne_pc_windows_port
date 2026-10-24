"""Offline tests that native Windows packaging contains the game-owned co-op event builder."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).with_name("patch_windows_package.py")
spec = importlib.util.spec_from_file_location("seamless_v40_packager", SCRIPT)
pkg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pkg
spec.loader.exec_module(pkg)

FIXTURE = '''#!/bin/bash
set -euo pipefail
cd bbport
cp -r scripts patches "$dest/"
find "$dest" -name __pycache__ -prune -exec rm -r {} +
out/pyenv/Scripts/python.exe -I packaging/windows/make_zip.py out/stage bbport-windows dist/bbport-windows.zip
'''


class PackagerTests(unittest.TestCase):
    def test_production_coop_script_staged_before_zip(self):
        result = pkg.transform(FIXTURE)
        self.assertIn("event_patcher=../tools/re/party_boss_events.py", result)
        self.assertIn('cp "$event_patcher" "$dest/tools/party_boss_events.py"', result)
        self.assertIn('cp "$credits" "$dest/CREDITS.txt"', result)
        self.assertIn('Missing downstream author and copyright notices', result)
        self.assertIn('Missing upstream GPL or required redistributed third-party notice', result)
        for required in ('FireBurn-FSR-Vulkan-LICENSE.txt', 'AMD-FidelityFX-SDK-LICENSE.txt',
                         'Intel-XeSS-LICENSE.txt', 'PkgTool-LICENSE.txt'):
            self.assertIn(required, result)
        self.assertLess(result.index(pkg.MARKER), result.index(pkg.ANCHOR))
        self.assertLess(result.index(pkg.MARKER), result.index("packaging/windows/make_zip.py"))
        self.assertIn('exit 1', result)
        self.assertNotIn("dvdroot_ps4/event", result)
        self.assertNotIn("event-reference.json", result)  # Requires actual game, no hash invented.

    def test_duplicate_patch_and_upstream_drift_stop(self):
        with self.assertRaisesRegex(ValueError, "already applied"):
            pkg.transform(pkg.transform(FIXTURE))
        with self.assertRaisesRegex(ValueError, "changed"):
            pkg.transform(FIXTURE.replace(pkg.ANCHOR, "echo surprise"))
        with self.assertRaisesRegex(ValueError, "absent"):
            pkg.transform(FIXTURE.replace("packaging/windows/make_zip.py", "missing.py"))
        with self.assertRaisesRegex(ValueError, "layout changed"):
            pkg.transform(FIXTURE.replace('cp -r scripts patches "$dest/"', ""))


if __name__ == "__main__":
    unittest.main()
