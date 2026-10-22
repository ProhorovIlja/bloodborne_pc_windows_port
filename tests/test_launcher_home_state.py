"""Offline contract checks for honest game/party readiness wording."""
import unittest

import paths  # noqa: F401
import launcher_home_state as hub


class HomeStateTests(unittest.TestCase):
    def test_game_never_claims_verified_without_preflight(self):
        self.assertIn("Choose", hub.game_label("", False))
        self.assertIn("invalid", hub.game_label("C:/games/Bloodborne", False))
        self.assertIn("before Play", hub.game_label("C:/games/Bloodborne/eboot.bin", True))
        self.assertIn("Bloodborne", hub.game_label("C:/games/Bloodborne/eboot.bin", True))
        self.assertNotIn("ready to play", hub.game_label("C:/games/Bloodborne/eboot.bin", True).lower())

    def test_native_client_is_not_runtime_validity(self):
        self.assertIn("missing", hub.client_label(False, True))
        self.assertIn("script missing", hub.client_label(True, False))
        self.assertIn("not yet verified", hub.client_label(True, True))

    def test_parties_do_not_claim_legacy_crossplay(self):
        self.assertIn("Solo", hub.party_label(""))
        self.assertIn("not CLS BBSC", hub.party_label("host"))
        self.assertIn("not CLS BBSC", hub.party_label("join"))
        self.assertIn("legacy BBSC not enabled", hub.party_label("unknown"))


if __name__ == "__main__":
    unittest.main()
