"""Source-pinned nonHosted original C++ roster memoization regression."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_nonhosted_roster_cache_v112.py")
spec = importlib.util.spec_from_file_location("yt130_v112_roster_cache", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeRosterCacheTests(unittest.TestCase):
    @staticmethod
    def fixture():
        return {
            m.HEADER: ("constexpr size_t TeamSize = 5;\n" +
                       m.H_OLD + "\n" + m.H_MEMBERS),
            m.CPP: ("constexpr std::array<u32, 4> GuestSigns{7, 6, 5, 4};\n" +
                    m.CPP_OLD),
            m.TEST: m.TEST_OLD,
        }

    def test_all_original_protocol_and_invalidation_contracts_unchanged(self):
        changed = m.rewrite(self.fixture())
        self.assertIn("nonhosted_roster_valid = false;", changed[m.HEADER])
        self.assertIn("mutable std::vector<bbcoop::LobbyPlayer> nonhosted_roster",
                      changed[m.HEADER])
        self.assertIn("nonhosted_roster.reserve(players.size());", changed[m.CPP])
        self.assertIn("entry.set_state(StateOf(other));", changed[m.CPP])
        self.assertIn("if (const bbcoop::Team* team = TeamOf(other))", changed[m.CPP])
        self.assertIn("if (entry.member() != member)", changed[m.CPP])
        self.assertIn("*state.add_players() = entry;", changed[m.CPP])
        self.assertIn("} else {", changed[m.CPP])  # original Hosted branch untouched
        self.assertIn("NonHostedRosterCacheRefreshesAndKeepsOriginalPerRecipientSemantics",
                      changed[m.TEST])
        for fragment in ("Request(Action::CREATE)", "Request(Action::INVITE",
                         "Request(Action::ACCEPT", "lobby.Leave(",
                         "lobby.SetHosted(", "SerializeAsString()"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, changed[m.TEST])
        self.assertEqual(m.BLOBS[m.HEADER],
                         "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8")
        self.assertEqual(m.BLOBS[m.CPP],
                         "7978d8d8062d8c18f1db79b02551c65fba2eb261")
        self.assertEqual(m.BLOBS[m.TEST],
                         "c045e637ada5e548b003d34033c912fde54f1d34")

    def test_fail_closed_incomplete_unpinned_and_repeated_patches(self):
        original = self.fixture()
        changed = m.rewrite(original)
        for case in (
            {**original, m.HEADER: original[m.HEADER].replace("TeamSize = 5",
                                                             "TeamSize = 4")},
            {**original, m.CPP: original[m.CPP].replace("GuestSigns{7, 6, 5, 4}",
                                                        "GuestSigns{7, 6, 5}")},
            {**original, m.HEADER: original[m.HEADER].replace(m.H_OLD, "BROKEN")},
            {**original, m.HEADER: original[m.HEADER].replace(m.H_MEMBERS, "BROKEN")},
            {**original, m.CPP: original[m.CPP].replace(m.CPP_OLD, "BROKEN")},
            {**original, m.TEST: original[m.TEST].replace(m.TEST_OLD, "BROKEN")},
            changed,
        ):
            with self.subTest(invalid=list(case.keys())):
                with self.assertRaises(ValueError):
                    m.rewrite(case)
        with self.assertRaises(ValueError):
            m.rewrite({m.HEADER: original[m.HEADER]})


if __name__ == "__main__":
    unittest.main()
