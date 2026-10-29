"""Validate the V112 nonHosted + PR41-derived V113 Hosted transforms TOGETHER."""
import importlib.util
from pathlib import Path
import unittest


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hosted = load("yt_v113", "stage_hosted_lobby_index_v113.py")
nonhosted = load("yt_v112", "stage_nonhosted_roster_cache_v112.py")


def original():
    # A deliberately minimal source fixture containing the *real exact*
    # pinned original anchors of both modules. The native Qt CI stages both
    # against the full original source and compiles/runs the real C++ tests.
    return {
        nonhosted.HEADER: (
            "constexpr size_t TeamSize = 5;\n" + nonhosted.H_OLD + "\n" +
            hosted.OLD_SET_HOSTED + "\n" + nonhosted.H_MEMBERS),
        nonhosted.CPP: (
            "constexpr std::array<u32, 4> GuestSigns{7, 6, 5, 4};\n" +
            nonhosted.CPP_OLD + "\n" + hosted.OLD_INDEX + "\n" +
            hosted.OLD_STATE),
        nonhosted.TEST: nonhosted.TEST_OLD,
    }


def compose():
    files = nonhosted.rewrite(original())
    cpp, header, tests = hosted.rewrite(
        files[nonhosted.CPP], files[nonhosted.HEADER],
        files[nonhosted.TEST])
    return cpp, header, tests


class CompositeRosterTests(unittest.TestCase):
    def test_both_lobby_modes_live_in_same_original_qt_server(self):
        cpp, header, tests = compose()
        self.assertIn("nonhosted_roster.reserve(players.size());", cpp)
        self.assertIn("hosted_solo_index.clear();", cpp)
        self.assertIn("hosted_invite_team_index.clear();", cpp)
        self.assertIn("for (const std::string& other : hosted_solo_index)", cpp)
        self.assertIn("for (const std::string& invited : found->second)", cpp)
        self.assertIn("nonhosted_roster_valid = false;", header)
        self.assertIn("Changed(); // Rebuild hosted indices", header)
        self.assertIn("NonHostedRosterCacheRefreshesAndKeepsOriginalPerRecipientSemantics",
                      tests)
        self.assertIn("HostedLargeTeamsKeepRosterBoundedThroughChanges", tests)
        self.assertIn("failed |= HostedLargeTeamsKeepRosterBoundedThroughChanges();",
                      tests)
        self.assertIn("failed |= NonHostedRosterCacheRefreshesAndKeepsOriginalPerRecipientSemantics();",
                      tests)
        self.assertIn("lobby.Leave(", tests)
        self.assertIn("lobby.SetHosted(", tests)
        self.assertEqual(tests.count("int main() {"), 1)

    def test_requires_verified_predecessor_and_forbids_repeat(self):
        base = original()
        with self.assertRaisesRegex(ValueError, "requires V112"):
            hosted.rewrite(base[nonhosted.CPP], base[nonhosted.HEADER],
                           base[nonhosted.TEST])
        cpp, header, tests = compose()
        with self.assertRaisesRegex(ValueError, "Double application"):
            hosted.rewrite(cpp, header, tests)

    def test_any_missing_source_anchor_fails_closed(self):
        base = nonhosted.rewrite(original())
        for field, value in (
            (nonhosted.CPP, hosted.OLD_INDEX),
            (nonhosted.CPP, hosted.OLD_STATE),
            (nonhosted.HEADER, hosted.OLD_HEADER),
            (nonhosted.HEADER, hosted.OLD_SET_HOSTED),
            (nonhosted.TEST, hosted.OLD_MAIN),
        ):
            broken = dict(base)
            broken[field] = broken[field].replace(value, "MISSING", 1)
            with self.subTest(field=field, anchor=value[:20]):
                with self.assertRaises(ValueError):
                    hosted.rewrite(broken[nonhosted.CPP],
                                   broken[nonhosted.HEADER],
                                   broken[nonhosted.TEST])

    def test_three_pinned_original_git_blobs_match(self):
        self.assertEqual(hosted.PIN, nonhosted.PIN)
        self.assertEqual(hosted.BLOBS, nonhosted.BLOBS)


if __name__ == "__main__":
    unittest.main()
