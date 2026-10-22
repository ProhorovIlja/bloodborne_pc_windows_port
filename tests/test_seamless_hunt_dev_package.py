"""Offline regression checks for the game-asset-free Seamless Hunt Windows dev ZIP."""
import paths  # noqa: F401
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.release import stage_seamless_hunt_dev as kit

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
            "out/SDL3.dll",
            "out/gpu/bbgpu.dll",
            "launcher/example.py",
        ]:
            f = self.root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(("TEST:" + name).encode("ascii"))
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
            self.assertNotIn("out/gpu/bbgpu.dll", names)
            self.assertIn("scripts/seamless_hunt.py", names)
            self.assertIn("patches/Bloodborne.xml", names)
            self.assertIn("licenses/LICENSE", names)
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

    def test_reject_invalid_revision(self):
        with self.assertRaisesRegex(ValueError, "40-character"):
            kit.pack(self.root, Path(self.temp.name) / "bad.zip", "main")


if __name__ == "__main__":
    unittest.main()
