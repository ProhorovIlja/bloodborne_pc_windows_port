"""Read-only pinned Hunter preview, using synthetic save fixtures only."""
import tempfile
import unittest
from pathlib import Path

import paths  # noqa: F401
import hunter_profiles as hp
import hunter_preview as prev
from test_hunter_profiles import make_slot


class PreviewTests(unittest.TestCase):
    def test_pin_is_only_metadata_and_rechecks_file(self):
        with tempfile.TemporaryDirectory() as directory:
            slot = Path(directory) / "userdata0000"
            slot.write_bytes(make_slot("Мария"))
            h = hp.read_slot(slot, source="native:pc")
            self.assertIsNotNone(h)
            before = slot.read_bytes()
            pin = prev.pin_from_hunter(h)
            self.assertEqual(set(pin), {"folder", "slot", "source"})
            self.assertIn("Мария", prev.label(prev.preview(pin)))
            self.assertIn("not the active game slot", prev.label(prev.preview(pin)))
            self.assertEqual(slot.read_bytes(), before)
            # Never preserve stale stats from a removed/malformed save.
            slot.write_bytes(b"corrupt")
            self.assertIsNone(prev.preview(pin))
            self.assertIn("unavailable", prev.label(prev.preview(pin)))

    def test_bad_paths_and_wrong_slots_are_rejected(self):
        self.assertIsNone(prev.validate_pin({}))
        self.assertIsNone(prev.validate_pin({"folder": "x", "slot": "userdata0010", "source": ""}))
        self.assertIsNone(prev.validate_pin({"folder": "x" * 3000, "slot": "userdata0000", "source": ""}))
        self.assertIsNone(prev.validate_pin({"folder": "foo\0bar", "slot": "userdata0000", "source": ""}))
        self.assertIsNone(prev.preview(None))
        with tempfile.TemporaryDirectory() as directory:
            p = {"folder": directory, "slot": "userdata0001", "source": "manual:folder"}
            self.assertEqual(prev.validate_pin(p), p)
            self.assertIsNone(prev.preview(p))


if __name__ == "__main__":
    unittest.main()
