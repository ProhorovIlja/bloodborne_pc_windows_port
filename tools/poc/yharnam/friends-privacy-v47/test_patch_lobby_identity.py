"""Pinned V48 authenticated link -> lobby / party identity source tests."""
import importlib.util
import sys
from pathlib import Path
import unittest

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location("shyt_v48_identity_patch",
                                               here / "patch_lobby_identity.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

WORLD = """#include "bloodborne_world.h"
    // The same run saying hello again
    const bool arrived = member.lobby.empty();
"""
HEADER = """    const BloodborneCoop::TeamLobby& Lobby() const {
    BloodborneCoop::TeamLobby lobby;
"""
LINK = """#include "link_server.h"
    // Phase 11: the hello signs the player in (its id's account is made the first time).
"""

def sources():
    return {m.WORLD: WORLD, m.WORLD_H: HEADER, m.LINK: LINK}

class SignedInLobbyMemberTests(unittest.TestCase):
    def test_both_world_and_lobby_are_account_bound(self):
        out = m.transform(sources())
        world = out[m.WORLD]
        self.assertEqual(world.count("SHYT-V48-LOBBY-ACCOUNT-BOUND"), 2)
        self.assertEqual(world.count("MatchesAuthenticatedMember("), 2)
        self.assertIn('welcome.set_text("Co-op member does not match', world)
        self.assertIn("Co-op lobby member does not match the authenticated account", world)
        self.assertEqual(out[m.LINK].count("m_world.RequireAuthenticatedIdentity();"), 1)
        self.assertIn("require_authenticated_identity = false", out[m.WORLD_H])
        self.assertIn("void RequireAuthenticatedIdentity()", out[m.WORLD_H])
        self.assertIn('#include "sh_lobby_identity.hpp"', world)

    def test_client_character_label_cannot_authorize_lobby_member(self):
        out = m.transform(sources())[m.WORLD]
        self.assertIn("member.online_id.constData()", out)
        self.assertIn("hello.member())", out)
        self.assertNotIn("hello.name())", out)

    def test_unknown_upstream_rejected_and_idempotence(self):
        original = sources()
        for path, old, new in [
            (m.WORLD, "The same run saying hello again", "The same saved game is back"),
            (m.WORLD, "const bool arrived = member.lobby.empty();", "const bool returned = true;"),
            (m.LINK, "Phase 11: the hello signs the player", "Phase 11: untrusted player"),
            (m.WORLD_H, "BloodborneCoop::TeamLobby& Lobby()", "BloodborneCoop::TeamLobby& Rooms()"),
        ]:
            changed = dict(original)
            changed[path] = changed[path].replace(old, new)
            with self.subTest(path=path, anchor=old), self.assertRaisesRegex(ValueError, "drifted"):
                m.transform(changed)
        with self.assertRaisesRegex(ValueError, "already applied"):
            m.transform(m.transform(original))

if __name__ == "__main__":
    unittest.main()
