"""V184 strict synthetic source regression for donor lobby-only setting.

Does not read private ZIPs, game files, real accounts, or run deployment.
"""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "yt184_lobby", Path(__file__).with_name("stage_cls_lobby_only_v184.py"))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def fixture(path: str) -> str:
    return "\n".join(old for old, _ in v.PATCHES[path])


class IndependentLobbyOnlyTests(unittest.TestCase):
    def test_every_exact_original_file_is_single_patch_and_drift_fails(self):
        self.assertEqual(len(v.PATCHES), 7)
        for path, changes in v.PATCHES.items():
            with self.subTest(path=path):
                initial = fixture(path)
                updated = v.rewrite(path, initial)
                self.assertNotEqual(updated, initial)
                for before, after in changes:
                    self.assertIn(after, updated)
                    self.assertEqual(initial.count(before), 1)
                # An already staged original-world source has no hosted-only
                # SendLobby anchor; it must fail closed, not look like dedupe.
                with self.assertRaisesRegex(ValueError, "anchor drift|unrecognized"):
                    v.rewrite(path, updated)
                with self.assertRaisesRegex(ValueError, "anchor drift"):
                    v.rewrite(path, initial.replace(changes[0][0], "SOURCE_DRIFT"))
                with self.assertRaisesRegex(ValueError, "anchor drift"):
                    v.rewrite(path, initial + "\n" + changes[0][0])

    def test_composes_with_prior_anonymous_nonhosted_lobby_dedupe(self):
        path = "server/src/bloodborne_world.cpp"
        original = fixture(path)
        old_block = v.PATCHES[path][1][0]
        safe_dedupe = (
            "void Service::SendLobby(qint64 now_ms) {\n"
            "            // A lobby-state envelope is delivered by CoopStream with ACKs\n"
            "            std::string bytes = envelope.lobby_state().SerializeAsString();\n"
            "            if (sent == bytes) continue;\n"
            "}\n")
        modified = original.replace(old_block, safe_dedupe)
        updated = v.rewrite(path, modified)
        self.assertIn("!LobbyLimited() || now_ms - lobby_sent_ms", updated)
        self.assertIn("lobby.SetLobbyCap(rules.lobby_players)", updated)
        self.assertEqual(updated.count("A lobby-state envelope is delivered"), 1)
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            v.rewrite(path, original.replace(old_block, "UNREVIEWED CHANGES"))

    def test_flag_off_and_hosted_unchanged(self):
        cfg = v.rewrite("server/src/config.cpp", fixture("server/src/config.cpp"))
        hdr = v.rewrite("server/src/config.h", fixture("server/src/config.h"))
        self.assertIn('boolean("LobbyLimits", false)', cfg)
        self.assertIn("bool lobbyLimits = false;", hdr)
        self.assertNotIn("LinkRateLimits", cfg)
        self.assertNotIn("SetRequiredBuild", v.PATCHES["server/src/link_server.cpp"][0][1])
        self.assertNotIn("m_guard", v.PATCHES["server/src/link_server.cpp"][0][1])
        self.assertNotIn("SetSignIn", v.PATCHES["server/src/link_server.cpp"][0][1])
        self.assertNotIn("MakeAccountsAtSignIn", cfg)

    def test_lobby_cap_not_world_or_team_access_control(self):
        lobby_h = v.rewrite("server/coop/team_lobby.h",
                            fixture("server/coop/team_lobby.h"))
        lobby_cpp = v.rewrite("server/coop/team_lobby.cpp",
                              fixture("server/coop/team_lobby.cpp"))
        world_h = v.rewrite("server/src/bloodborne_world.h",
                            fixture("server/src/bloodborne_world.h"))
        world_cpp = v.rewrite("server/src/bloodborne_world.cpp",
                              fixture("server/src/bloodborne_world.cpp"))
        self.assertIn("capped = true;", lobby_h)
        self.assertIn("if (!hosted && !capped)", lobby_cpp)
        self.assertIn("return hosted.enabled || hosted.lobby_limits;", world_h)
        self.assertIn("else if (rules.lobby_limits)", world_cpp)
        self.assertIn("lobby.SetHosted(rules.lobby_players, rules.worlds_per_player)", world_cpp)
        self.assertIn("lobby.SetLobbyCap(rules.lobby_players)", world_cpp)
        self.assertNotIn("worlds_per_player =", v.PATCHES["server/coop/team_lobby.h"][0][1])
        self.assertNotIn("m_hosted.enabled = true", v.PATCHES["server/src/link_server.cpp"][0][1])

    def test_throttle_and_deduplicate_lobby_only_no_packet_grading(self):
        cpp = v.rewrite("server/src/bloodborne_world.cpp",
                        fixture("server/src/bloodborne_world.cpp"))
        self.assertIn("!LobbyLimited() || now_ms - lobby_sent_ms >=", cpp)
        self.assertIn("if (LobbyLimited())", cpp)
        self.assertNotIn("LinkRateLimits", cpp)
        self.assertNotIn("RoutesPacket", cpp)
        self.assertNotIn("SHYT_ENABLE_TEST_LOCAL_MTLS", cpp)
        self.assertEqual(v.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")

if __name__ == "__main__":
    unittest.main()
