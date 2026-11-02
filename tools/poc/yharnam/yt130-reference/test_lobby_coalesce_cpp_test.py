"""Pin source and check actual co-op event behavior test is not weakened."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_lobby_coalesce_cpp_test.py")
spec = importlib.util.spec_from_file_location("yt130_cpp_lobby", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class LobbyCPPTestGuards(unittest.TestCase):
    def test_source_staging_adds_real_lobby_behavior_and_registration(self):
        original = "header\n" + mod.ANCHOR + "      {\"ExistingTest\", ExistingTest},\n  };\n"
        after = mod.patch_text(original)
        self.assertEqual(after.count('{"NonHostedTeamEditsAreCoalescedAndStartStillWorks"'), 1)
        for expression in (
            "leader.lobby_states == before_leader + 1",
            "guest.lobby_states == before_guest + 1",
            "newcomer.lobby_states >= 1",
            "guest.lobby.invites_size() == 1",
            "leader.starts.back().party() == guest.starts.back().party()",
            "leader.lobby_states == steady",
            "guest.Team(bbcoop::TeamRequest::ACCEPT,",
        ):
            self.assertIn(expression, after)
        with self.assertRaises(ValueError):
            mod.patch_text(after)

    def test_pin_and_ambiguous_original_fail(self):
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(mod.BLOB, "2ec55d02101545723e9889bebe83d8b1d531a1c7")
        for original in ("", mod.ANCHOR + mod.ANCHOR):
            with self.assertRaises(ValueError):
                mod.patch_text(original)

if __name__ == "__main__":
    unittest.main()
