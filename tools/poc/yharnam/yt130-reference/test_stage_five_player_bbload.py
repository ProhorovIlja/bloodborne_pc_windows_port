"""Offline five-player bbload source-guard tests (no live connections)."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_five_player_bbload.py")
spec = importlib.util.spec_from_file_location("five_bbload_test", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FivePlayerLoadgenTests(unittest.TestCase):
    def test_only_exact_two_source_anchors_rewritten(self):
        original = 'before\n' + mod.OLD_HELP + '\n' + mod.OLD_CLAMP + '\nafter'
        transformed = mod.rewrite(original)
        self.assertEqual(transformed.count(mod.NEW_HELP), 1)
        self.assertEqual(transformed.count(mod.NEW_CLAMP), 1)
        self.assertNotIn(mod.OLD_CLAMP, transformed)
        self.assertNotIn(mod.OLD_HELP, transformed)
        self.assertEqual(transformed.splitlines()[0], "before")

    def test_missing_duplicate_and_second_stage_refused(self):
        original = mod.OLD_HELP + "\n" + mod.OLD_CLAMP
        for invalid in (original + "\n" + mod.OLD_HELP,
                        original.replace(mod.OLD_CLAMP, ""),
                        mod.rewrite(original)):
            with self.assertRaisesRegex(ValueError, "source anchor drift"):
                mod.rewrite(invalid)

    def test_unpinned_source_refused(self):
        with self.assertRaisesRegex(ValueError, "exact official pinned"):
            mod.transform((mod.OLD_HELP + mod.OLD_CLAMP).encode())


if __name__ == "__main__":
    unittest.main()
