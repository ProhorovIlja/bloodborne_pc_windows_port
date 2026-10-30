"""Test fail-closed V136 native P2PTransport source integration and locking."""
from pathlib import Path
import ast
import importlib.util
import unittest

base=Path(__file__).parent
sp=importlib.util.spec_from_file_location("game_owner_v136",base/"patch_native_game_direct_owner_v136.py")
mod=importlib.util.module_from_spec(sp)
assert sp and sp.loader
sp.loader.exec_module(mod)
clock=importlib.util.spec_from_file_location("time_v135",base/"patch_native_clock_domain_v135.py")
v135=importlib.util.module_from_spec(clock)
assert clock and clock.loader
clock.loader.exec_module(v135)

def old_method():
    source=(base/"patch_native_game_aead_drop_guard.py").read_text()
    tree=ast.parse(source)
    for func in ast.walk(tree):
        if isinstance(func,ast.Assign):
            if any(isinstance(target,ast.Name) and target.id=="method" for target in func.targets):
                return ast.literal_eval(func.value)
    raise ValueError("Original V106 game-owned crypto-only native code missing")

def original_composed_fixture():
    return "\n".join([
        "// SHYT-V135-NATIVE-AUTH-UTC-CLOCK",
        "// SHYT-V87-TRUSTED-SERVER-LINK",
        "// SHYT-V92-ORIGINAL-SOCKET-SIGNED-PROBE",
        v135.AFTER,
        mod.INCLUDE_OLD,
        mod.MEMBER_OLD,
        mod.SEND_OLD,
        v135.INGRESS_AFTER,
        "void test() { native_shy2_egress.Seal(game_frame); }",
        old_method(),mod.METHOD_END,
        "void stop() {",mod.REVOKE_OLD,"}",
        "void configure() {",mod.REVOKE_OLD,"}",
        "void other() { nat_probe_v92.reset(); }",
    ])

class NativeOwnerTests(unittest.TestCase):
    def test_original_game_stages_one_dev_only_encrypted_route(self):
        rewritten=mod.patch_game(original_composed_fixture())
        self.assertEqual(rewritten.count(mod.MARKER),2)
        self.assertEqual(rewritten.count("SignedNatRouteLeaseV134::ArmAfterVerifiedCrypto("),1)
        self.assertIn("SeamlessHunt::Hybrid::NativeGameSelfIdentityV87::Digest(",rewritten)
        self.assertIn("SecureOfferV84Detail::EqualDigest(",rewritten)
        self.assertIn("std::lock_guard direct_lock(direct_egress_mutex);",rewritten)
        self.assertIn("std::lock_guard grant_lock(native_grant_mutex);",rewritten)
        self.assertIn("native_signed_route_v136.signed_nat_proof=&*nat_probe_v92;",rewritten)
        self.assertIn("direct_egress.RevokeAll();",rewritten)
        self.assertIn("native_shy2_ingress.Revoke(0)",rewritten)
        self.assertIn("native_shy2_egress.Revoke(0)",rewritten)
        self.assertEqual(rewritten.count("native_signed_route_v136={};"),3)
        self.assertEqual(rewritten.count("P2PAuthEpochMs()"),4)
        self.assertEqual(rewritten.count("SHYT_ENABLE_TEST_LOCAL_MTLS")>=5,True)
        # Unreliable-only Direct remains original V71; server Coop, RPC and
        # reliable GameLink classes are not reclassified by this source patch.
        self.assertIn(mod.SEND_NEW,rewritten)
        self.assertNotIn("direct_egress.Arm(",rewritten)
        self.assertNotIn("native_shy2_ingress.Arm(",rewritten)

    def test_refuses_repeat_or_missing_authority_and_revoke_paths(self):
        original=original_composed_fixture()
        with self.assertRaises(ValueError):mod.patch_game(mod.patch_game(original))
        for cut in (mod.INCLUDE_OLD,mod.MEMBER_OLD,mod.SEND_OLD,
                    mod.METHOD_START, "SHYT-V92-ORIGINAL-SOCKET-SIGNED-PROBE",
                    "SHYT-V135-NATIVE-AUTH-UTC-CLOCK"):
            with self.subTest(anchor=cut[:32]):
                with self.assertRaises(ValueError):
                    mod.patch_game(original.replace(cut,"SOURCE_CHANGED"))
        with self.assertRaises(ValueError):
            mod.patch_game(original.replace(mod.REVOKE_OLD,"BROKEN",1))

if __name__=="__main__":unittest.main()
