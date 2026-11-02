"""Test the actual offline installer verifier, never upload/install game files."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SRC = Path(__file__).with_name("verify_installer.py")
sp = importlib.util.spec_from_file_location("yt130_release", SRC)
m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)

class VerifiedReleaseV130(unittest.TestCase):
    def test_manifest_tracks_published_upstream_digest_not_a_game_asset(self):
        data = json.loads(Path(__file__).with_name("release.json").read_text())
        self.assertEqual(data["tag"], "v1.3.0")
        self.assertEqual(data["source_sha"], "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(data["installer_bytes"], 126842039)
        self.assertEqual(data["installer_sha256"], "9482f2d0c2cee0bd637f79db463d6efe63cace52ac39a69ad88bf8471b431a55")

    def test_accept_exact_content_then_reject_tamper_truncation_symlink(self):
        raw = b"synthetic-non-game-test-installer-bytes"
        digest = hashlib.sha256(raw).hexdigest()
        with TemporaryDirectory() as td:
            path = Path(td) / "sample.exe"
            path.write_bytes(raw)
            self.assertEqual(m.check(path, len(raw), digest), digest)
            with self.assertRaisesRegex(ValueError, "size mismatch"):
                m.check(path, len(raw) - 1, digest)
            path.write_bytes(raw[:-1] + b"!")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                m.check(path, len(raw), digest)
            link = Path(td) / "alias.exe"
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                m.check(link, len(raw), digest)

if __name__ == "__main__":
    unittest.main()
