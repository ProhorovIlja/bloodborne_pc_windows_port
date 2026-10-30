"""Native YT1.3 P2P time-domain regression, not a game launch claim."""
import importlib.util
from pathlib import Path
import unittest

modpath=Path(__file__).with_name("patch_native_clock_domain_v135.py")
spec=importlib.util.spec_from_file_location("yt135",modpath)
yt135=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(yt135)

class ClockDomainTests(unittest.TestCase):
    def fixture(self):
        return ("\n".join([
            "// SHYT-V71-NATIVE-DIRECT-TX",
            "// SHYT-SHY2-AUTHENTICATED-INGRESS",
            "// SHYT-SHY2-ENCRYPTED-GAME-UDP",
            "// SHYT-V87-TRUSTED-SERVER-LINK",
            "// SHYT-V92-ORIGINAL-SOCKET-SIGNED-PROBE",
            yt135.BEFORE,
            "void example() {",
            "auto decision = direct_egress.TrySend(",
            yt135.DIRECT_BEFORE,
            yt135.INGRESS_BEFORE,
            "bool LinkCut() const { return P2PNowMs() < link_cut_until_ms.load(); }",
            "auto local_tick = P2PNowMs();",
            "}"
        ]))
    def test_original_transport_only_crypto_uses_epoch_clock(self):
        before=self.fixture()
        patched=yt135.patch_game(before)
        self.assertEqual(patched.count("P2PAuthEpochMs()"),3)
        self.assertEqual(patched.count("P2PNowMs()"),3)
        self.assertIn("std::chrono::system_clock::now()",patched)
        self.assertIn("std::chrono::steady_clock::now()",patched)
        self.assertIn("P2PNowMs() < link_cut_until_ms",patched)
        self.assertIn(yt135.DIRECT_AFTER,patched)
        self.assertIn(yt135.INGRESS_AFTER,patched)
        self.assertNotIn(yt135.DIRECT_BEFORE,patched)
        self.assertNotIn(yt135.INGRESS_BEFORE,patched)
        self.assertNotIn("direct_egress.Arm(",patched)
        self.assertNotIn("native_shy2_ingress.Arm(",patched)

    def test_drift_double_stage_and_unauthorized_arm_denied(self):
        before=self.fixture()
        with self.assertRaises(ValueError):
            yt135.patch_game(yt135.patch_game(before))
        for anchor in (yt135.BEFORE,yt135.DIRECT_BEFORE,yt135.INGRESS_BEFORE,
                       "SHYT-V87-TRUSTED-SERVER-LINK"):
            with self.subTest(anchor=anchor[:25]):
                with self.assertRaises(ValueError):
                    yt135.patch_game(before.replace(anchor,"BROKEN"))
        with self.assertRaises(ValueError):
            yt135.patch_game(before+"direct_egress.Arm(")

    def test_explicit_utc_relative_to_system_and_not_steady(self):
        self.assertTrue(yt135.AFTER.startswith(yt135.BEFORE))
        self.assertIn("std::chrono::system_clock::now()",yt135.AFTER)
        self.assertIn("std::chrono::steady_clock::now()",yt135.BEFORE)
        self.assertIn("P2PAuthEpochMs()",yt135.DIRECT_AFTER)
        self.assertIn("P2PAuthEpochMs()",yt135.INGRESS_AFTER)

if __name__=="__main__":
    unittest.main()
