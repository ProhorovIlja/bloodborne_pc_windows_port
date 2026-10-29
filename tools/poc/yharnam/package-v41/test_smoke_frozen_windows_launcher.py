import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).with_name("smoke_frozen_windows_launcher.py")
spec = importlib.util.spec_from_file_location("shyt_launcher_smoke", SCRIPT_PATH)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class FrozenLauncherSmokeUnit(unittest.TestCase):
    def test_cyrillic_script_compiles_and_writes_expected_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Проверка" / "проверка.py"
            path.parent.mkdir(parents=True)
            target = path.parent / "результат.txt"
            path.write_text(smoke.SCRIPT, encoding="utf-8")
            code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
            capture = io.StringIO()
            with mock.patch.object(sys, "argv", [str(path), str(target)]):
                with contextlib.redirect_stdout(capture):
                    exec(code, {"__name__": "__main__", "__file__": str(path)})
            self.assertEqual(target.read_text(encoding="utf-8"),
                             smoke.EXPECTED_MARKER)
            self.assertIn(smoke.EXPECTED_STDOUT, capture.getvalue())

    def test_archive_rejects_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("bbport-windows/BLauncher.exe", b"MZ")
            smoke.inspect_archive(archive)
            with zipfile.ZipFile(archive, "a") as z:
                z.writestr("bbport-windows/../password.key", b"secret")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                smoke.inspect_archive(archive)

    def test_case_collisions_denied_on_windows(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "case-collision.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("bbport-windows/BLauncher.exe", b"MZ")
                z.writestr("bbport-windows/README.TXT", "first")
                z.writestr("bbport-windows/readme.txt", "second")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                smoke.inspect_archive(archive)

    def test_symlink_payload_denied_before_extract(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "symlink.zip"
            link = zipfile.ZipInfo("bbport-windows/escape.txt")
            link.create_system = 3
            link.external_attr = (0o120777 << 16)
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("bbport-windows/BLauncher.exe", b"MZ")
                z.writestr(link, "../../outside")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                smoke.inspect_archive(archive)

    def test_missing_frozen_launcher_denied(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("bbport-windows/README.txt", "No launcher")
            with self.assertRaisesRegex(ValueError, "BLauncher.exe"):
                smoke.inspect_archive(archive)


if __name__ == "__main__":
    unittest.main()
