"""Regression tests against extracted, pinned Yharnam Together BLauncher Tk UI."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shyt_v56_onboarding", HERE / "patch_onboarding.py")
patch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = patch
spec.loader.exec_module(patch)
PINNED = (HERE / "pinned_coop_onboarding_fixture.py").read_text(encoding="utf-8")


class OnboardingTests(unittest.TestCase):
    def test_complete_pinned_launcher_popup_transforms_and_compiles(self):
        output = patch.transform(PINNED)
        compile(output, "bbport_launcher_win.py", "exec")
        self.assertIn("SHYT_LAUNCHER_ONBOARDING_V56", output)
        self.assertIn("Seamless Hunt  |  ", output)
        self.assertIn("Yharnam Together  ·  Co-op", output)
        self.assertIn("self.coop_setup_progress.configure(", output)
        self.assertIn("Yharnam Together server IP", output)
        self.assertIn("No other multiplayer client is required", output)
        self.assertIn("CONTINUE", output)
        self.assertIn("key != 'harder'", output)
        self.assertIn("self.coop_picked.add(key)", output)
        self.assertIn("self.coop_done.configure(state='disabled' if missing else 'normal')", output)
        # No new password persistence or extra account credentials.
        self.assertNotIn("password_entry", output)
        self.assertNotIn("def switch_provider", output)
        self.assertNotIn("shadps4", output.lower())
        self.assertNotIn("supermedo", output.lower())
        # The original first-run actions must remain wired and interactive.
        for action in ("self.coop_browse", "self.coop_search(None)",
                       "self.coop_import_saves", "self.open_coop_help",
                       "self.close_coop", "self.coop_changed",
                       "self.build_coop_custom"):
            self.assertIn(action, output)

    def test_first_run_difficulty_defaults_to_vanilla_only(self):
        output = patch.transform(PINNED)
        self.assertIn("if self.coop.get('confirmed') != '1' and key != 'harder':", output)
        self.assertIn("self.coop_picked.add(key)", output)
        # No change to the actual hard mode values, custom modifiers or
        # settings persistence: only the first-run choice UX is altered.
        self.assertEqual(output.count("self.coop_custom_changed()"),
                         PINNED.count("self.coop_custom_changed()"))
        self.assertEqual(output.count("bbport_coop.save_settings"),
                         PINNED.count("bbport_coop.save_settings"))

    def test_missing_pinned_launcher_anchor_is_not_ignored(self):
        broken = PINNED.replace("def build_coop_popup(self):", "def different_popup(self):")
        # The interior is still present, so move an actual uniquely guarded anchor.
        broken = broken.replace("self.coop_vars, self.coop_picked = {}, set()", "")
        with self.assertRaisesRegex(ValueError, "drift"):
            patch.transform(broken)
        with self.assertRaisesRegex(ValueError, "already installed"):
            patch.transform(patch.transform(PINNED))

    def test_real_game_and_connection_settings_not_rewritten(self):
        output = patch.transform(PINNED)
        for raw in ("self.coop.get('game', '')", "bbport_coop.valid_ip(",
                    "self.coop['role'] =", "self.coop['confirmed'] = '1'"):
            # These methods may be outside the fixture, but if present,
            # source transformation must preserve the exact code.
            if raw in PINNED:
                self.assertIn(raw, output)

if __name__ == "__main__":
    unittest.main()
