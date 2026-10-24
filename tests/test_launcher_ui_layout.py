"""Windows Tk smoke check: the actual launcher home, scrollable settings and log UI."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

import paths  # noqa: F401


@unittest.skipUnless(sys.platform == "win32", "Windows Tk smoke runs only on windows-latest")
class LauncherUiLayoutTests(unittest.TestCase):
    def test_compact_home_and_existing_settings_remain_reachable(self):
        import launcher
        # Keep this a pure UI smoke; real game/network/GPU checks have their own tests.
        with patch.object(launcher, "connected_displays", return_value=[]), \
             patch.object(launcher, "connected_gamepads", return_value=[]), \
             patch.object(launcher.BloodborneLauncher, "start_update_check"), \
             patch.object(launcher.BloodborneLauncher, "discover_installs"), \
             patch.object(launcher.BloodborneLauncher, "check_last_party_session"):
            app = launcher.BloodborneLauncher()
            try:
                app.update_idletasks()
                self.assertEqual(app.settings_panel.winfo_manager(), "")
                self.assertFalse(app.settings_open)
                self.assertFalse(app.diagnostics_open)
                self.assertEqual(app.diagnostics_log_frame.winfo_manager(), "")
                self.assertTrue(app.home_game_var.get())
                self.assertTrue(app.home_party_var.get())
                self.assertGreaterEqual(len(app.notebook.tabs()), 7)

                app.show_settings_section("Party")
                app.update_idletasks()
                self.assertTrue(app.settings_open)
                self.assertEqual(app.settings_panel.winfo_manager(), "pack")
                self.assertEqual(app.notebook.tab(app.notebook.select(), "text"), "Party")
                self.assertEqual(app.settings_canvas.winfo_manager(), "pack")
                app.show_settings_section("Performance & Shaders")
                self.assertEqual(app.notebook.tab(app.notebook.select(), "text"),
                                 "Performance & Shaders")
                app.hide_settings_panel()
                self.assertFalse(app.settings_open)
                self.assertEqual(app.settings_panel.winfo_manager(), "")
                app.toggle_diagnostics()
                self.assertTrue(app.diagnostics_open)
                self.assertEqual(app.diagnostics_log_frame.winfo_manager(), "pack")
                app.toggle_diagnostics()
                self.assertFalse(app.diagnostics_open)
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
