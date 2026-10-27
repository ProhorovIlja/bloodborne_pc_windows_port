"""Upstream-author PR430 Windows executable version resource QA.

Source is GPL-2.0-or-later original lKaniel PR430. Standalone suite runs on
any OS, and Windows PyInstaller additionally probes the VERSION resource.
"""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).with_name("version_info.py")
spec = importlib.util.spec_from_file_location("yt_pr430_version_info", FILE)
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)


class FrozenLauncherVersionTests(unittest.TestCase):
    def test_original_author_stable_resource(self):
        self.assertEqual(version.PRODUCT, "Yharnam Together: Bloodborne Seamless Co-op")
        self.assertEqual(version.COMPANY, "Yharnam Together")
        self.assertIn("GPL-2.0-or-later", version.COPYRIGHT)
        self.assertEqual(version.numbers("1.3.0-qa.1"), (1, 3, 0, 0))
        self.assertEqual(version.numbers("1.3.1-rc.2"), (1, 3, 1, 0))

    def test_ast_and_original_exe_metadata(self):
        text = version.text("1.3.0-qa.1")
        ast.parse(text, mode="eval")
        for needed in ("BLauncher.exe", "Yharnam Together", "GPL-2.0-or-later",
                       "filevers=(1, 3, 0, 0)", "StringStruct('ProductName'"):
            self.assertIn(needed, text)

    def test_native_pyinstaller_file_parses_if_installed(self):
        try:
            from PyInstaller.utils.win32 import versioninfo
        except ImportError:
            self.skipTest("Windows PyInstaller not installed for this source-only step")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "BLauncher-version.txt"
            version.write("1.3.0-qa.1", path)
            info = versioninfo.load_version_info_from_text_file(str(path))
            self.assertEqual(
                (info.ffi.fileVersionMS, info.ffi.fileVersionLS),
                ((1 << 16) | 3, 0),
            )


if __name__ == "__main__":
    unittest.main()
