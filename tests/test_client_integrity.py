"""Offline integrity diagnostics: no downloads, game files or real user saves."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import paths  # noqa: F401
import client_integrity as checker


class ClientIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "extracted"
        self.root.mkdir()
        self.files = {name: (name + ":test").encode("utf-8") for name in checker.REQUIRED}
        self.files["patches/Bloodborne.xml"] = b"<patch>owner changed</patch>"
        self.files["CHANGELOG.md"] = b"# Unreleased"
        self.write_build()

    def write_build(self):
        manifest = []
        for rel, content in self.files.items():
            file = self.root / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
            manifest.append({"path": rel, "bytes": len(content),
                             "sha256": hashlib.sha256(content).hexdigest()})
        data = {"format": checker.FORMAT, "source_commit": "a" * 40,
                "files": manifest}
        (self.root / "MANIFEST.json").write_text(json.dumps(data), encoding="utf-8")

    def test_pristine_and_untracked_user_files_never_examined(self):
        private = self.root / "user" / "savedata" / "1" / "secret.save"
        private.parent.mkdir(parents=True)
        private.write_bytes(b"SAVE SECRET")
        local_settings = self.root / "launcher_settings.json"
        local_settings.write_text('{"account": "PRIVATE"}', encoding="utf-8")
        with mock.patch("client_integrity._hash_file", wraps=checker._hash_file) as hashed:
            report = checker.verify_installed(self.root)
            hashed_paths = [call.args[0].resolve() for call in hashed.call_args_list]
            self.assertNotIn(private.resolve(), hashed_paths)
            self.assertNotIn(local_settings.resolve(), hashed_paths)
        self.assertEqual(report.critical_errors, 0)
        self.assertEqual(report.optional_changes, 0)
        self.assertFalse(report.as_dict()["source_authenticity_verified"])
        self.assertFalse(report.as_dict()["save_files_examined"])
        self.assertEqual(private.read_bytes(), b"SAVE SECRET")
        self.assertIn("NOT forged packages", checker.summary(report))

    def test_changed_core_file_and_optional_patches(self):
        (self.root / "out" / "bbport.exe").write_bytes(b"tampered")
        (self.root / "patches" / "Bloodborne.xml").write_bytes(b"custom patch")
        report = checker.verify_installed(self.root)
        self.assertEqual(report.critical_errors, 1)
        self.assertEqual(report.optional_changes, 1)
        self.assertIn("CORE CLIENT", checker.summary(report))
        self.assertIn("out/bbport.exe (mismatch)", checker.summary(report))
        self.assertIn("Optional: patches/Bloodborne.xml", checker.summary(report))

    def test_missing_core_file_and_invalid_manifest(self):
        (self.root / "python" / "python312.dll").unlink()
        self.assertEqual(checker.verify_installed(self.root).critical_errors, 1)
        data = json.loads((self.root / "MANIFEST.json").read_text())
        data["files"][0]["path"] = "user/savedata/secret"
        (self.root / "MANIFEST.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Unsafe manifest path"):
            checker.verify_installed(self.root)

    def test_case_collision_and_bad_hash(self):
        data = json.loads((self.root / "MANIFEST.json").read_text())
        data["files"].append({**data["files"][0], "path": data["files"][0]["path"].upper()})
        (self.root / "MANIFEST.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            checker.verify_installed(self.root)
        data["files"].pop()
        data["files"][0]["sha256"] = "0" * 60
        (self.root / "MANIFEST.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Invalid build-file"):
            checker.verify_installed(self.root)

    def test_refuse_symlink_even_if_hash_matches(self):
        slot = self.root / "launcher.py"
        target = self.root / "launcher-copy"
        target.write_bytes(slot.read_bytes())
        slot.unlink()
        try:
            slot.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Filesystem cannot create symlink")
        report = checker.verify_installed(self.root)
        self.assertEqual(report.critical_errors, 1)
        self.assertIn("launcher.py (unsafe)", checker.summary(report))

    def test_modification_during_hashing_is_detected(self):
        real = checker._hash_file
        def modified(path):
            value = real(path)
            if path.name == "bbport.exe":
                path.write_bytes(path.read_bytes() + b"extra")
            return value
        with mock.patch("client_integrity._hash_file", side_effect=modified):
            report = checker.verify_installed(self.root)
        self.assertEqual(report.critical_errors, 1)

    def test_missing_manifest_not_success(self):
        (self.root / "MANIFEST.json").unlink()
        with self.assertRaisesRegex(ValueError, "No installed build manifest"):
            checker.verify_installed(self.root)

    def test_path_schema_is_strict(self):
        for path in ["../out/bbport.exe", "user/savedata/1/hero",
                     "mods/cheat.dll", "out/gpu/bbnet20.dll",
                     "scripts/../launcher.py", "out\\bbport.exe",
                     "C:/Windows/System32/a.dll", "python/site-packages/evil.py",
                     "scripts/.git/config"]:
            self.assertFalse(checker._valid_rel(path), path)
        self.assertTrue(checker._valid_rel("python/DLLs/_tkinter.pyd"))
        self.assertTrue(checker._valid_rel("out/licenses/SDL3/LICENSE.txt"))


if __name__ == "__main__":
    unittest.main()
