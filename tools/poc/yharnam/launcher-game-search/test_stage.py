"""Offline source exact fail-closed tests for native game-search safety patch."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage.py")
spec = importlib.util.spec_from_file_location("game_search_stage", p)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class StageTests(unittest.TestCase):
    def setUp(self):
        self.src = (stage.OLD_IS_GAME + "\nNOT_A_MATCH\n" +
                    stage.OLD_FIND + "\nNOT_A_MATCH\n" + stage.OLD_FIRST)

    def test_exact_and_reversible(self):
        after = stage.patch_text(self.src)
        self.assertIn("except OSError:", after)
        self.assertIn("Keep searching instead of breaking setup.", after)
        self.assertIn("if folder else None", after)
        self.assertNotIn(stage.OLD_IS_GAME, after)
        with self.assertRaises(ValueError):
            stage.patch_text(after)

    def test_missing_ambiguous_or_modified_anchors_fail(self):
        for s in (self.src.replace("Path(folder) / 'eboot.bin'",
                                   "Path(folder) / 'something.exe'"),
                  self.src + stage.OLD_FIND,
                  self.src.replace("found = find_game_folder(folder, 2)",
                                   "found = find_game_folder(folder, 3)")):
            with self.subTest(changed=s[-100:]):
                with self.assertRaises(ValueError):
                    stage.patch_text(s)

    def test_only_original_native_launcher_file_is_allowed(self):
        self.assertEqual(stage.FILE, "bbport/launcher/bbport_coop.py")
        self.assertEqual(stage.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(stage.BLOB, "9c54b2cd577b1fd4d50cd500c64c0b9d0f1e8b24")


if __name__ == "__main__":
    unittest.main()
