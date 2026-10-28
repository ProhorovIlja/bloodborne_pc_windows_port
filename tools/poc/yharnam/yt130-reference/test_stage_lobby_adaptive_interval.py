"""Fail-closed checks for adaptive full nonHosted lobby snapshot fanout."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name("stage_lobby_adaptive_interval.py")
spec = importlib.util.spec_from_file_location("yt130_adaptive_lobby", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class AdaptiveLobbyTests(unittest.TestCase):
    def original(self):
        cpp = ("void Service::OnLobbyHello() {}\n"
               "void Service::Settle() {}\n"
               "void Service::SendLobby(qint64 now_ms) {}\n" + m.OLD_TICK)
        test = ("int NonHostedTeamEditsAreCoalescedAndStartStillWorks() { return 0; }\n"
                + m.OLD_TEST)
        return cpp, test

    def test_small_session_unchanged_and_larger_sessions_bounded(self):
        cpp, test = m.rewrite(*self.original())
        self.assertIn("members.size() >= 128 ? 500", cpp)
        self.assertIn("members.size() >= 64 ? 250 : 0", cpp)
        self.assertIn("hosted.enabled ? hosted.lobby_interval_ms", cpp)
        self.assertIn("if (lobby_changed && now_ms - lobby_sent_ms >= lobby_interval_ms)", cpp)
        self.assertIn("SendLobby(now_ms);", cpp)
        self.assertNotIn("lobby.SetHosted(", cpp)
        self.assertNotIn("OnLobbyHello(", m.NEW_TICK)
        self.assertNotIn("TeamStart", m.NEW_TICK.replace("synchronous TeamStart", ""))
        self.assertIn("NonHostedFullLobbyIsAdaptiveWithoutDelayingFirstHello", test)
        self.assertIn("CHECK(players[1]->lobby_states == before);", test)
        self.assertIn("CHECK(players[1]->lobby.invites_size() == 1);", test)
        self.assertIn("CHECK(players.back()->lobby_states >= 1);", test)

    def test_fails_closed_if_upstream_or_previous_stage_drifted(self):
        src = self.original()
        output = m.rewrite(*src)
        with self.assertRaises(ValueError):
            m.rewrite(*output)
        with self.assertRaises(ValueError):
            m.rewrite(src[0].replace("SendLobby(now_ms);", "DoNotSend();"), src[1])
        with self.assertRaises(ValueError):
            m.rewrite(src[0], m.OLD_TEST)
        with self.assertRaises(ValueError):
            m.rewrite(src[0].replace("void Service::OnLobbyHello(", "void OnNoHello("), src[1])

    def test_exact_official_original_yt130_source_pins(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "eca8c30d6fb78099b0f64a52388fd7d65f926e19")
        self.assertEqual(m.BLOBS[m.TEST], "2ec55d02101545723e9889bebe83d8b1d531a1c7")

if __name__ == "__main__":
    unittest.main()
