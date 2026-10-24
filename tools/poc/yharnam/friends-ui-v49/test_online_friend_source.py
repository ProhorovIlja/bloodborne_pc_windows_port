"""Security and compatibility contracts for the V49 source patch.

The whole V3-V49 composition test also runs; these checks capture the UI
capability boundary so a future change cannot silently expose peer data or
pretend to support unimplemented friend invasions.
"""
from pathlib import Path
import unittest

SOURCE = (Path(__file__).parent / "patch_online_friends.py").read_text("utf-8")

class OnlineMutualFriendContracts(unittest.TestCase):
    def test_only_authenticated_server_relationships_may_mark_friends(self):
        for fragment in (
            "m_db.GetUserId", "m_db.GetRelationships", "m_db.GetRelStatus",
            "FriendStatus::Blocked", "live->appearOffline",
            "visible_friends(member.online_id)", "player.set_mutual_friend(true)",
            "shyt-mutual-friends-filter",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, SOURCE)

    def test_existing_invite_no_unreviewed_join_or_invasion(self):
        self.assertIn("bbcoop_lobby_request(BBCOOP_TEAM_INVITE, p.id)", SOURCE)
        self.assertNotIn("BBCOOP_TEAM_INVADE", SOURCE)
        self.assertNotIn("BBCOOP_TEAM_JOIN_ANYWAY", SOURCE)
        self.assertIn("static bool show_mutual_friends_only = false", SOURCE)
        self.assertIn("if (show_mutual_friends_only && !p.mutual_friend) continue", SOURCE)

    def test_protobuf_extension_is_backward_compatible_and_non_authoritative(self):
        self.assertIn("bool mutual_friend = 12;", SOURCE)
        self.assertIn("server-computed, recipient-only", SOURCE)
        self.assertIn("member.online_id", SOURCE)
        self.assertIn("player.mutual_friend()", SOURCE)

if __name__ == "__main__":
    unittest.main()
