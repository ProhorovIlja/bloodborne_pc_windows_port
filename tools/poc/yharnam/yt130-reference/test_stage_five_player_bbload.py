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
                '\n'.join(old for old, _ in mod.RECEIVER_EDITS) + '\n' +
                # Four V120 anchors predate all earlier source transforms.
                '\n'.join(mod.STEADY_EDITS[i][0] for i in (0, 1, 2, 4))
                + '\nafter')

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
            # V118 deliberately extends several V117 receiver edit results;
            # validate their final composed form, not obsolete intermediates.
            final = after
            for old, replacement in mod.FULL_TEAM_EDITS:
                if old in final:
                    final = final.replace(old, replacement, 1)
            for old, replacement in mod.STEADY_EDITS:
                if old in final:
                    final = final.replace(old, replacement, 1)
            self.assertIn(final, transformed)
        self.assertIn("game_receivers += game->Playing() && game->SawGamePackets();",
                      transformed)
        self.assertEqual(len(mod.FULL_TEAM_EDITS), 4)
        self.assertIn("complete_teams += game->CompleteTeam(settings.team_size);",
                      transformed)
        self.assertIn('{"complete_teams", complete_teams}', transformed)
        self.assertIn("seat == 0 && state == State::Playing && team_members == expected",
                      transformed)
        self.assertEqual(len(mod.STEADY_EDITS), 6)
        self.assertIn("steady_since_us = now_us;", transformed)
        self.assertIn("steady_packets_sent += frame.entries.size();", transformed)
        self.assertIn("steady_packets_received;", transformed)
        self.assertIn('{"steady_window_ms", steady_since_us ?', transformed)
        self.assertIn("static_cast<s64>(sent) >= load.steady_since_us", transformed)
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

    def test_missing_full_team_anchor_rejected(self):
        # Inspect the EXACT previous source transformation, before V118 edits.
        prior = self.pinned_anchor_fixture()
        prior = prior.replace(mod.OLD_HELP, mod.NEW_HELP, 1)
        prior = prior.replace(mod.OLD_CLAMP, mod.NEW_CLAMP, 1)
        for old, new in mod.OWNER_EDITS:
            prior = prior.replace(old, new, 1)
        for old, new in mod.RECEIVER_EDITS:
            prior = prior.replace(old, new, 1)
        for old, _ in mod.FULL_TEAM_EDITS:
            with self.subTest(missing=old[:40]):
                self.assertEqual(prior.count(old), 1)
                with self.assertRaisesRegex(ValueError,
                                            "complete-five-team bbload anchor drift"):
                    mod.patch_complete_teams(prior.replace(old, "BROKEN", 1))
        self.assertIn("complete_teams", mod.patch_complete_teams(prior))

    def test_missing_real_steady_counter_anchor_fails_closed(self):
        prior = self.pinned_anchor_fixture()
        prior = prior.replace(mod.OLD_HELP, mod.NEW_HELP, 1)
        prior = prior.replace(mod.OLD_CLAMP, mod.NEW_CLAMP, 1)
        for old, new in mod.OWNER_EDITS:
            prior = prior.replace(old, new, 1)
        for old, new in mod.RECEIVER_EDITS:
            prior = prior.replace(old, new, 1)
        prior = mod.patch_complete_teams(prior)
        for old, _ in mod.STEADY_EDITS:
            with self.subTest(steady=old[:45]):
                self.assertEqual(prior.count(old), 1)
                with self.assertRaisesRegex(ValueError,
                                            "steady five-hunter game payload anchor drift"):
                    mod.patch_steady_window(prior.replace(old, "BROKEN", 1))
        self.assertIn("steady_packets_received",
                      mod.patch_steady_window(prior))

    def test_duplicate_game_start_is_not_modified_by_load_steady_patch(self):
        # Exact upstream bbload has started_us in BOTH Game and Load.
        game_decl = "struct Game {\n  s64 started_us = 0;\n};\n"
        original = game_decl + self.pinned_anchor_fixture()
        self.assertEqual(original.count("  s64 started_us = 0;\n"), 2)
        transformed = mod.rewrite(original)
        self.assertIn(game_decl, transformed)
        self.assertIn(
            "  Totals totals;\n  s64 started_us = 0;\n"
            "  s64 steady_since_us = 0; // set once, after real full-team Playing\n",
            transformed,
        )

    def test_unpinned_source_refused(self):
        with self.assertRaisesRegex(ValueError, "exact official pinned"):
            mod.transform((mod.OLD_HELP + mod.OLD_CLAMP).encode())


if __name__ == "__main__":
    unittest.main()
