"""Functional native YT1.3 game discovery regression on real staged Python source.

Run with PYTHONPATH=<disposable YT1.3 bbport/launcher> to prove actual
functions work, not just string replacement. Uses only temporary fake folders.
"""
import tempfile
from pathlib import Path
from unittest import mock
import unittest
import bbport_coop as coop


class RealLauncherGameSearchPermissions(unittest.TestCase):
    def test_eboot_is_file_permission_error_is_nonfatal(self):
        orig = Path.is_file
        def restricted(file):
            if file.name == "eboot.bin" and "blocked" in file.parts:
                raise PermissionError(13, "mock restricted game folder", str(file))
            return orig(file)
        with mock.patch.object(Path, "is_file", restricted):
            self.assertFalse(coop.is_game_folder(Path("/mock/blocked")))
            self.assertFalse(coop.is_bloodborne(Path("/mock/blocked")))

    def test_nearby_restricted_folder_skipped_and_real_bloodborne_found(self):
        orig = Path.is_file
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a-blocked").mkdir()
            (root / "z-game").mkdir()
            (root / "z-game" / "eboot.bin").write_bytes(b"game")
            def restricted(file):
                if file.name == "eboot.bin" and "a-blocked" in file.parts:
                    raise PermissionError(13, "mock inaccessible directory", str(file))
                return orig(file)
            with mock.patch.object(Path, "is_file", restricted):
                self.assertEqual(coop.find_game_folder(root, depth=2), root / "z-game")
                self.assertEqual(
                    coop.search_game(root / "install", drives=[], homes=[],
                                     depth=2, near=root / "a-blocked"),
                    root / "z-game")

    def test_missing_or_inaccessible_first_path_yields_none(self):
        orig_is_dir = Path.is_dir
        def forbidden(path):
            if path.name == "blocked":
                raise PermissionError(13, "blocked", str(path))
            return orig_is_dir(path)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(Path, "is_dir", forbidden):
                self.assertIsNone(coop.find_game_folder(root / "blocked"))
                self.assertIsNone(coop.search_game(
                    root / "install", drives=[], homes=[],
                    depth=1, near=root / "blocked"))


if __name__ == "__main__":
    unittest.main()
