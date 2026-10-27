"""Source exact integration gate for author original YT Windows launcher PR #433."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage.py")
spec = importlib.util.spec_from_file_location("yt_win_unicode", p)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class Pr433ImportSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = stage.PATCH.read_text(encoding="utf-8")

    def test_unchanged_author_patch_two_files(self):
        stage.validate(self.patch)
        self.assertEqual(stage.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(stage.BLOB, "b54974c649610bef59e53a61ae294edc2d386cda")
        self.assertEqual(len(stage.HEADER.findall(self.patch)), 2)

    def test_never_accepts_unrelated_game_or_server_files(self):
        with self.assertRaises(ValueError):
            stage.validate(self.patch + "\ndiff --git a/server/world.cpp b/server/world.cpp\n")
        with self.assertRaises(ValueError):
            stage.validate(self.patch.replace("bbport/tests/test_launcher_code_page.py",
                                              "server/accounts.cpp"))

    def test_also_requires_actual_cyrillic_and_crash_tests(self):
        for feature in ("CYRILLIC", "faulthandler", "launcher-errors.txt",
                        "reconfigure(encoding='utf-8', errors='replace', line_buffering=True)",
                        "test_the_log_goes_to_temp_when_the_install_cannot_be_written"):
            with self.subTest(feature=feature):
                with self.assertRaises(ValueError):
                    stage.validate(self.patch.replace(feature, "REMOVED_TEXT"))

    def test_no_customer_files_or_source_archive_replacement(self):
        self.assertEqual(stage.FILE, "bbport/launcher/bbport_launcher_win.py")
        self.assertEqual(stage.ADDED_TEST, "bbport/tests/test_launcher_code_page.py")
        self.assertNotIn("server/", "\n".join(x[0] for x in stage.HEADER.findall(self.patch)))


if __name__ == "__main__":
    unittest.main()
