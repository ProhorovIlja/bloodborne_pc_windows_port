#!/usr/bin/env python3
"""V87 exact native game accepted-Welcome identity and link-epoch guard tests."""
from pathlib import Path
import importlib.util
import unittest
p=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("native_v87",p/"patch_native_link_identity_v87.py")
v87=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v87)
GAME='''// SHYT-V86-NATIVE-FULL-ID-TLS
#include "core/libraries/network/sh_native_tls_local_client_v85.hpp" // SHYT-V86-NATIVE-FULL-ID-TLS
    SeamlessHunt::Hybrid::NativeSealedGrantInboxV84 native_grant_inbox_v84{};
    void ConfigureLink(std::string online_id,std::string secret) {
        {
            std::lock_guard lock(link_mutex);
            link_online_id = std::move(online_id);
            link_secret = std::move(secret);
        }
    }
    void SetLinkBuild(std::string build) {
        if (Link::SaysHelloAgainForBuild(link_build, build)) {
            link_welcomed = false;
            link_hello_ms.reset();
        }
    }
    void OnWelcome() {
                first = !link_welcomed;
                link_welcomed = true;
                link_refusal.clear();
    }
    void LinkHousekeeping() {
            if (quiet) {
                // The server may have restarted and forgotten this game: say hello again.
                link_welcomed = false;
            }
    }
    bool TryLocalShg2OfferForTest(
        const SeamlessHunt::Hybrid::NativeTlsLocalConfig& cfg,
        const SeamlessHunt::Hybrid::NativeOfferIdentityV84& expected,
        std::uint64_t serial,
        SeamlessHunt::Hybrid::RefreshNativeOfferIdentityV84 current,
        void* verified_game_state,std::uint64_t now_ms) {
        std::lock_guard lock(native_grant_mutex);
        return SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
            cfg,native_grant_inbox_v84,expected,serial,current,
            verified_game_state,now_ms);
    }
    std::string link_online_id;
    std::string link_secret;
'''
class IdentityPatch(unittest.TestCase):
    def test_game_link_is_source_of_self_identity(self):
        s=v87.patch_game(GAME)
        self.assertEqual(s.count(v87.MARKER),1)
        self.assertIn("NativeGameSelfIdentityV87::MatchesAcceptedLink(",s)
        self.assertIn("original_online_id=link_online_id",s)
        self.assertIn("original_generation=shyt_link_generation_v87",s)
        self.assertIn("shyt_link_generation_v87==original_generation",s)
        self.assertIn("native_grant_inbox_v84.Revoke();",s)
        self.assertEqual(s.count("BumpLocalLinkGenerationV87();"),4)
        self.assertIn("std::fill(original_online_id.begin()",s)
        self.assertIn("if(!running.load(std::memory_order_acquire)",s)
        self.assertIn("SHYT_ENABLE_TEST_LOCAL_MTLS",s)
        self.assertNotIn("direct_egress.Arm(",s)
        self.assertNotIn("SendFrame(",s)
        with self.assertRaisesRegex(ValueError,"already integrated"):
            v87.patch_game(s)

    def test_reject_source_drift_and_missing_welcome(self):
        for s in (
            GAME.replace("SHYT-V86-NATIVE-FULL-ID-TLS",""),
            GAME.replace("link_online_id = std::move(online_id);","link_online_id = online_id;"),
            GAME.replace("link_secret = std::move(secret);","link_secret = secret;"),
            GAME.replace("first = !link_welcomed;","first=false;"),
            GAME.replace("The server may have restarted and forgotten this game","The game was restarted"),
            GAME.replace("std::string link_online_id;","std::string online_name;"),
            GAME.replace("NativeTlsLocalOfferClientV85::Request","NativeTlsLocalOfferClientV83::Request"),
        ):
            with self.subTest(variation=s[-70:]),self.assertRaises(ValueError):
                v87.patch_game(s)
if __name__=="__main__":
    unittest.main()
