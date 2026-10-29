"""Offline five-player bbload source-guard tests (no live connections)."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_five_player_bbload.py")
spec = importlib.util.spec_from_file_location("five_bbload_test", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FivePlayerLoadgenTests(unittest.TestCase):
    @staticmethod
    def pinned_anchor_fixture():
        return ('before\n' + mod.OLD_HELP + '\n' + mod.OLD_CLAMP + '\n' +
                '\n'.join(old for old, _ in mod.OWNER_EDITS) + '\n' +
                '\n'.join(old for old, _ in mod.RECEIVER_EDITS) + '\nafter')

    def test_exact_upstream_pr444_owner_changes_and_five_player_anchors(self):
        original = self.pinned_anchor_fixture()
        transformed = mod.rewrite(original)
        self.assertEqual(transformed.count(mod.NEW_HELP), 1)
        self.assertEqual(transformed.count(mod.NEW_CLAMP), 1)
        self.assertNotIn(mod.OLD_CLAMP, transformed)
        self.assertNotIn(mod.OLD_HELP, transformed)
        self.assertEqual(len(mod.OWNER_EDITS), 7)
        self.assertEqual(len(mod.RECEIVER_EDITS), 5)
        for before, after in mod.RECEIVER_EDITS:
            self.assertIn(after, transformed)
        self.assertIn("game_receivers += game->Playing() && game->SawGamePackets();",
                      transformed)
        for old, new in mod.OWNER_EDITS:
            self.assertIn(new, transformed)
        self.assertIn('std::clamp(parser.value("owners").toInt(), 1, settings.team_size)',
                      transformed)
        self.assertIn('Owner() ? load.settings.owner_fps', transformed)
        self.assertEqual(transformed.splitlines()[0], "before")

    def test_missing_duplicate_and_second_stage_refused(self):
        original = self.pinned_anchor_fixture()
        for invalid in (original + "\n" + mod.OLD_HELP,
                        original.replace(mod.OLD_CLAMP, ""),
                        mod.rewrite(original)):
            with self.assertRaisesRegex(ValueError, "anchor drift"):
                mod.rewrite(invalid)
        for old, new in mod.OWNER_EDITS:
            with self.subTest(missing=old[:40]):
                with self.assertRaisesRegex(ValueError, "multi-owner.*anchor drift"):
                    mod.rewrite(original.replace(old, "MISSING", 1))

    def test_missing_receiver_source_anchor_is_rejected(self):
        original = self.pinned_anchor_fixture()
        for before, _ in mod.RECEIVER_EDITS:
            with self.subTest(anchor=before[:30]):
                with self.assertRaisesRegex(ValueError, "game-receiver.*anchor drift"):
                    mod.rewrite(original.replace(before, "MISSING", 1))

    def test_unpinned_source_refused(self):
        with self.assertRaisesRegex(ValueError, "exact official pinned"):
            mod.transform((mod.OLD_HELP + mod.OLD_CLAMP).encode())


if __name__ == "__main__":
    unittest.main()
