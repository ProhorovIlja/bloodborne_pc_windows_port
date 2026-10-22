"""Offline search tests: no Tk window, game, network or user data needed."""
import unittest

from scripts.settings_index import search_entries


class SettingsSearchTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            ("Graphics", "Frame generation:"),
            ("Display", "Frames ahead:"),
            ("Party", "Max players:"),
            ("Party", "Password:"),
            ("Advanced / Debug", "Save support bundle..."),
            ("Graphics", "Frame generation:"),
            ("Game", "Русский текст"),
        ]

    def test_exact_and_prefix_rank_first(self):
        self.assertEqual(search_entries(self.entries, "frame generation"), [0])
        self.assertEqual(search_entries(self.entries, "frame"), [0, 1])

    def test_tab_and_label_terms(self):
        self.assertEqual(search_entries(self.entries, "party password"), [3])
        self.assertEqual(search_entries(self.entries, "support bundle"), [4])

    def test_unicode_and_casefold(self):
        self.assertEqual(search_entries(self.entries, "РУССКИЙ"), [6])

    def test_limit_dedup_and_empties(self):
        self.assertEqual(search_entries(self.entries, "frame", limit=1), [0])
        self.assertEqual(search_entries(self.entries, "graphics"), [0])
        self.assertEqual(search_entries(self.entries, "  ..."), [])
        self.assertEqual(search_entries(self.entries, "", limit=200), [])

    def test_no_sensitive_values(self):
        # Entries are labels only; user secrets never form part of the index.
        self.assertEqual(search_entries(self.entries, "my-secret-password"), [])


if __name__ == "__main__":
    unittest.main()
