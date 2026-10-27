"""Integration tests running REAL patched YT1.3 native Windows launcher code.

These tests use temporary throwaway files and fault injection, never user
settings or game saves. Intent is non-destructive failure behavior.
"""
import json
import os
from pathlib import Path
import tempfile
from unittest import mock
import unittest

import bbport_launcher_win as launcher


class NativeAtomicFileTests(unittest.TestCase):
    def test_atomic_utf8_replaces_complete_old_json(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            target.write_text('{"old":"safe"}\n', encoding="utf-8")
            settings = {"профиль": "Охотник 🎮", "online": True}
            launcher.atomic_utf8_write(
                target, json.dumps(settings, ensure_ascii=False, indent=2))
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), settings)
            self.assertFalse(list(Path(folder).glob("*.tmp")))
            self.assertFalse(list(Path(folder).glob(".*.tmp")))

    def test_interrupted_atomic_rename_preserves_existing_bytes_and_no_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bbport.ini"
            original = b"frame_cap=60\n# KEEP\n"
            path.write_bytes(original)
            with mock.patch.object(launcher.os, "replace",
                                   side_effect=PermissionError("Windows sharing violation")):
                with self.assertRaises(PermissionError):
                    launcher.atomic_utf8_write(path, "frame_cap=999\n")
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_failed_flush_fsync_preserves_original_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mods.json"
            original = b'{"order": ["old"]}\n'
            path.write_bytes(original)
            with mock.patch.object(launcher.os, "fsync",
                                   side_effect=OSError("disk flush failed")):
                with self.assertRaises(OSError):
                    launcher.atomic_utf8_write(path, '{"order":["new"]}')
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_new_path_creates_no_partials_even_if_rename_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "patches.json"
            with mock.patch.object(launcher.os, "replace",
                                   side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    launcher.atomic_utf8_write(path, '{"enabled":["all"]}')
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_settings_write_requires_existing_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "missing" / "settings.json"
            with self.assertRaises(OSError):
                launcher.atomic_utf8_write(target, "{}")
            self.assertFalse(target.exists())

    def test_ini_content_and_existing_comments_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bbport.ini"
            original_ini = "# my own settings\nframe_cap=60\nowner=русский\n"
            path.write_text(original_ini, encoding="utf-8")
            with mock.patch.object(launcher, "ini_path", return_value=path):
                launcher.save_ini({"frame_cap": "120"}, original_ini.splitlines())
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "# my own settings\nframe_cap=120\nowner=русский\n")


if __name__ == "__main__":
    unittest.main()
