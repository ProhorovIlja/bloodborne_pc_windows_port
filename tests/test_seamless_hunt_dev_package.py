"""Offline regression checks for the game-asset-free Seamless Hunt Windows dev ZIP."""
import paths  # noqa: F401
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.release import stage_seamless_hunt_dev as kit
from tools.release import verify_seamless_hunt_dev as checker
from scripts import client_integrity

SHA = "a" * 40


class DeveloperKitTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        for name in kit.REQUIRED:
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(("TEST:" + name).encode("ascii"))
        for name in [
            "scripts/seamless_hunt.py",
            "patches/Bloodborne.xml",
            "patches/redzone.json",
            "licenses/LICENSE",
            "licenses/GPL-3.0.txt",
            "out/licenses/LICENSE",
            "CHANGELOG.md",
            "out/licenses/msys2/PACKAGES.txt",
            "out/licenses/third_party/monocypher/LICENCE.md",
            "out/SDL3.dll",
            "out/gpu/bbgpu.dll",
            # The experimental REAL shadNet BBSC Win64 DLL is not a release:
            # even a successful compiler/linker test must never ship it.
            "out/gpu/bbnet20.dll",
            "launcher/example.py",
        ]:
            f = self.root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(("TEST:" + name).encode("ascii"))
        # The included Python runtime supports double-click GUI without a system Python.
        for name in (
            "python/python.exe", "python/pythonw.exe", "python/python312.dll",
            "python/LICENSE.txt", "python/LICENSE-tcltk.txt",
            "python/Lib/tkinter/__init__.py", "python/Lib/json/__init__.py",
            "python/DLLs/_tkinter.pyd", "python/tcl/tk8.6/tk.tcl",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("PY:" + name).encode("ascii"))
        # These must NEVER make it into a downloadable dev kit:
        for name in [
            "user/savedata/1/character.bin",
            "user/account_token.json",
            "launcher/local-settings.json",
            "scripts/secret.txt",
            "out/game/CUSA03173/eboot.bin",
            "out/shad_log.txt",
            "mods/private_mod/config.json",
            "cfg.ini",
        ]:
            f = self.root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("secret")

    def test_only_explicit_files_are_packaged_and_hashed(self):
        out = Path(self.temp.name) / "client.zip"
        result = kit.pack(self.root, out, SHA)
        self.assertEqual(result["source_commit"], SHA)
        with zipfile.ZipFile(out) as archive:
            names = set(archive.namelist())
            self.assertIn("out/bbport.exe", names)
            self.assertIn("python/python.exe", names)
            self.assertIn("python/pythonw.exe", names)
            self.assertIn("python/DLLs/_tkinter.pyd", names)
            self.assertIn("python/tcl/tk8.6/tk.tcl", names)
            self.assertNotIn("out/gpu/bbgpu.dll", names)
            self.assertNotIn("out/gpu/bbnet20.dll", names)
            self.assertIn("scripts/seamless_hunt.py", names)
            self.assertIn("CHANGELOG.md", names)
            self.assertIn("scripts/client_integrity.py", names) if (self.root / "scripts/client_integrity.py").is_file() else None
            self.assertIn("patches/Bloodborne.xml", names)
            self.assertIn("licenses/LICENSE", names)
            self.assertIn("out/licenses/LICENSE", names)
            self.assertIn("out/licenses/msys2/PACKAGES.txt", names)
            self.assertIn("README-DEVELOPER-BUILD.txt", names)
            self.assertIn("MANIFEST.json", names)
            for denied in (
                "user/account_token.json", "user/savedata/1/character.bin",
                "launcher/local-settings.json", "scripts/secret.txt",
                "out/game/CUSA03173/eboot.bin", "out/shad_log.txt",
                "mods/private_mod/config.json", "cfg.ini",
            ):
                self.assertNotIn(denied, names)
            manifest = json.loads(archive.read("MANIFEST.json"))
            self.assertEqual(manifest["source_commit"], SHA)
            for entry in manifest["files"]:
                self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(),
                                 entry["sha256"])
                self.assertEqual(len(archive.read(entry["path"])), entry["bytes"])
            self.assertNotIn("MANIFEST.json", [e["path"] for e in manifest["files"]])

    def test_deterministic_bytes(self):
        first = Path(self.temp.name) / "one.zip"
        second = Path(self.temp.name) / "two.zip"
        kit.pack(self.root, first, SHA)
        kit.pack(self.root, second, SHA)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_fails_closed_without_native_binary(self):
        (self.root / "out/bbport.exe").unlink()
        with self.assertRaisesRegex(ValueError, "Missing file"):
            kit.pack(self.root, Path(self.temp.name) / "bad.zip", SHA)

    def test_python_bundle_is_required(self):
        (self.root / "python/python.exe").unlink()
        with self.assertRaisesRegex(ValueError, "Missing file"):
            kit.pack(self.root, Path(self.temp.name) / "bad.zip", SHA)

    def test_reject_untrusted_python_runtime_payload(self):
        hidden = self.root / "python" / "site-packages" / "credentials.json"
        hidden.parent.mkdir(parents=True, exist_ok=True)
        hidden.write_text("do not include")
        with self.assertRaisesRegex(ValueError, "Unexpected Python runtime file"):
            kit.pack(self.root, Path(self.temp.name) / "bad.zip", SHA)

    def test_archive_is_verified_without_extraction(self):
        path = Path(self.temp.name) / "valid.zip"
        kit.pack(self.root, path, SHA)
        status = checker.verify(path)
        self.assertEqual(status["source_commit"], SHA)
        self.assertTrue(status["portable_python"])
        self.assertFalse(status["live_coop_verified"])
        self.assertIn("CHANGELOG.md", [x["path"] for x in json.loads(zipfile.ZipFile(path).read("MANIFEST.json"))["files"]])

    def test_extracted_build_manifest_matches_files_and_detects_corruption(self):
        source = Path(self.temp.name) / "portable.zip"
        extracted = Path(self.temp.name) / "portable"
        kit.pack(self.root, source, SHA)
        with zipfile.ZipFile(source) as z:
            z.extractall(extracted)
        report = client_integrity.verify_installed(extracted)
        self.assertEqual(report.critical_errors, 0)
        self.assertEqual(report.optional_changes, 0)
        self.assertEqual(report.revision, SHA)
        # A custom XML patch is a non-core difference: never delete or alter it.
        xml = extracted / "patches" / "Bloodborne.xml"
        xml.write_bytes(b"<custom/>")
        changed = client_integrity.verify_installed(extracted)
        self.assertEqual(changed.critical_errors, 0)
        self.assertEqual(changed.optional_changes, 1)
        self.assertEqual(xml.read_bytes(), b"<custom/>")
        (extracted / "out" / "bbport.exe").write_bytes(b"damaged runtime")
        self.assertEqual(client_integrity.verify_installed(extracted).critical_errors, 1)

    def test_reject_modified_file_with_stale_manifest(self):
        source = Path(self.temp.name) / "source.zip"
        tampered = Path(self.temp.name) / "tampered.zip"
        kit.pack(self.root, source, SHA)
        with zipfile.ZipFile(source) as z, zipfile.ZipFile(tampered, "w") as out:
            for info in z.infolist():
                raw = z.read(info.filename)
                if info.filename == "launcher.py":
                    raw = b"tampered content"
                out.writestr(info, raw)
        with self.assertRaisesRegex(ValueError, "content hash mismatch"):
            checker.verify(tampered)

    def test_reject_zip_traversal_and_windows_case_collision(self):
        for name in ("../user/savedata/secret.bin", "Launcher.py"):
            path = Path(self.temp.name) / (name.replace("/", "_") + ".zip")
            kit.pack(self.root, path, SHA)
            with zipfile.ZipFile(path, "a") as z:
                z.writestr(name, "not allowed")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe|colliding"):
                checker.verify(path)

    def test_reject_invalid_revision(self):
        with self.assertRaisesRegex(ValueError, "40-character"):
            kit.pack(self.root, Path(self.temp.name) / "bad.zip", "main")


if __name__ == "__main__":
    unittest.main()
