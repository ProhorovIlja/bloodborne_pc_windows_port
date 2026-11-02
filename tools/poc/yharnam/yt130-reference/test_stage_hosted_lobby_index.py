"""Pinned Hosted StateFor index semantics before original C++ compiles."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name("stage_hosted_lobby_index.py")
spec = importlib.util.spec_from_file_location("yt_lobby_index", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HostedSourceIndexTests(unittest.TestCase):
    def original(self):
        cpp = "start\n" + m.OLD_INDEX + "\n" + m.OLD_STATE + "\nend"
        header = m.OLD_SET_HOSTED + "\n" + m.OLD_HEADER
        tests = m.OLD_MAIN
        return cpp, header, tests

    def test_removes_repeated_full_roster_and_invite_scans(self):
        cpp, header, test = m.rewrite(*self.original())
        self.assertIn("hosted_solo_index.clear()", cpp)
        self.assertIn("hosted_invite_team_index.clear()", cpp)
        self.assertIn("hosted_invite_team_index[invite.team()].push_back(invited)", cpp)
        self.assertIn("for (const std::string& other : hosted_solo_index)", cpp)
        self.assertIn("for (const std::string& invited : found->second)", cpp)
        self.assertIn("if (!team_index.contains(member))", cpp)
        self.assertNotIn("for (const auto& [other, player] : players) {\n"
                         "            if (others >= lobby_players)", cpp)
        self.assertNotIn("for (const auto& [invited, list_of] : invites)", cpp)
        self.assertIn("Changed(); // Rebuild hosted indices", header)
        self.assertIn("HostedLargeTeamsKeepRosterBoundedThroughChanges", test)
        self.assertIn("failed |= HostedLargeTeamsKeepRosterBoundedThroughChanges();", test)

    def test_original_nonhosted_team_lookup_not_modified(self):
        cpp, header, _ = m.rewrite(*self.original())
        self.assertIn("team_index.emplace(m.member(), at);", cpp)
        self.assertIn("indexed = true;", cpp)
        self.assertIn("mutable std::map<std::string, size_t> team_index;", header)
        self.assertEqual(cpp.count("StateFor("), 0)  # marker is not an invocation
        self.assertNotIn("HandleLink(", cpp)
        self.assertNotIn("team_index.erase(", cpp)

    def test_fail_closed_on_mutated_source_and_duplicate_apply(self):
        cpp, header, test = self.original()
        updated = m.rewrite(cpp, header, test)
        with self.assertRaises(ValueError):
            m.rewrite(*updated)
        with self.assertRaises(ValueError):
            m.rewrite(cpp.replace("indexed = true;", "indexed = false;"),
                      header, test)
        with self.assertRaises(ValueError):
            m.rewrite(cpp, header.replace("this->lobby_players = lobby_players;",
                                          "this->lobby_players = 0;"), test)
        with self.assertRaises(ValueError):
            m.rewrite(cpp, header, test + m.OLD_MAIN)

    def test_pins_exact_original_three_cpp_files(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "7978d8d8062d8c18f1db79b02551c65fba2eb261")
        self.assertEqual(m.BLOBS[m.HEADER], "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8")
        self.assertEqual(m.BLOBS[m.TEST], "c045e637ada5e548b003d34033c912fde54f1d34")


if __name__ == "__main__":
    unittest.main()
