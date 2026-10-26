"""Validate isolated upstream source staging without a live server."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("stage_auth.py")
spec = importlib.util.spec_from_file_location("shyt_yt130_stage", SCRIPT)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class PinnedAuthStageSafety(unittest.TestCase):
    def make_fixtures(self, temp: str):
        root = Path(temp)
        checkout, overrides = root / "upstream", root / "overrides"
        paths = ["server/src/database.h", "server/src/link_server.cpp"]
        originals = {}
        for relative in paths:
            original = checkout / relative
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(("original_" + relative).encode())
            candidate = overrides / relative
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(("SHYT-AUTH-2026 repaired " + relative).encode())
            originals[relative] = stage.blob(original.read_bytes())
        return checkout, overrides, originals, paths

    def call(self, overrides: Path, checkout: Path, expected, head=None, dirty=False):
        outputs = [
            (head if head is not None else stage.PIN) + "\n",
            " M server/src/database.h\n" if dirty else "",
        ]
        with patch.object(stage, "SOURCE_BLOBS", expected), \
             patch.object(stage.subprocess, "check_output", side_effect=outputs):
            stage.main(overrides, checkout)

    def test_valid_stage_modifies_only_isolated_checkout(self):
        with tempfile.TemporaryDirectory() as td:
            checkout, overrides, hashes, names = self.make_fixtures(td)
            self.call(overrides, checkout, hashes)
            for p in names:
                self.assertIn(b"SHYT-AUTH-2026", (checkout / p).read_bytes())
                self.assertIn(b"SHYT-AUTH-2026", (overrides / p).read_bytes())

    def test_reject_wrong_pin_dirty_checkout_and_old_blob(self):
        with tempfile.TemporaryDirectory() as td:
            checkout, overrides, hashes, names = self.make_fixtures(td)
            with self.assertRaisesRegex(ValueError, "pinned"):
                self.call(overrides, checkout, hashes, head="deadbeef")
            with self.assertRaisesRegex(ValueError, "non-clean"):
                self.call(overrides, checkout, hashes, dirty=True)
            (checkout / names[-1]).write_bytes(b"unauthorized drift")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self.call(overrides, checkout, hashes)
            self.assertNotIn(b"SHYT-AUTH-2026", (checkout / names[0]).read_bytes())

    def test_reject_missing_override_and_same_directory(self):
        with tempfile.TemporaryDirectory() as td:
            checkout, overrides, hashes, names = self.make_fixtures(td)
            (overrides / names[-1]).unlink()
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self.call(overrides, checkout, hashes)
            with self.assertRaisesRegex(ValueError, "separate"):
                self.call(checkout, checkout, hashes)


if __name__ == "__main__":
    unittest.main()
