#!/usr/bin/env python3
"""V92 fail-closed game source adapter: same UDP socket, default-inert."""
import importlib.util
from pathlib import Path
import unittest

root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "shyt_v92",root/"patch_native_same_socket_probe_v92.py")
v92=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v92)

SOURCE='''// SHYT-V87-TRUSTED-SERVER-LINK
#include "core/libraries/network/sh_native_game_identity_v87.hpp" // SHYT-V87-TRUSTED-SERVER-LINK
    SeamlessHunt::Hybrid::NativeSealedGrantInboxV84 native_grant_inbox_v84{};
    std::uint64_t shyt_link_generation_v87=1;
    void Stop() {
        std::lock_guard lock(native_grant_mutex);
            native_grant_inbox_v84.Revoke(); // V86 logout/sockets closed
    }
    void ConfigureLink() {
        std::lock_guard lock(native_grant_mutex);
            native_grant_inbox_v84.Revoke(); // V86 account/server change
    }
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
public:
    bool TryLocalShg2OfferForTest() {
        const bool received=SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
            cfg,native_grant_inbox_v84,expected,serial,current,
            verified_game_state,now_ms);
        return received;
    }
private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(
    void ReceiveMain() {
        const auto rc = ::recvfrom(host_socket, nullptr,0,0,nullptr,nullptr);
        if (!FirewallAllows(from.sin_addr.s_addr, from.sin_port, "a datagram from")) {
                continue;
            }
            const std::span<const u8> datagram{buffer.data(), static_cast<size_t>(rc)};
            if (const auto server = LinkServer();
                server.addr_nbo == from.sin_addr.s_addr && server.port_nbo == from.sin_port) {
                continue;
            }
    }
'''
class V92Tests(unittest.TestCase):
    def test_probe_on_exact_original_udp_socket_not_game_route(self):
        result=v92.patch_game(SOURCE)
        self.assertEqual(result.count(v92.TAG),1)
        self.assertIn("TryPairedTlsReadyForNatTest(",result)
        self.assertIn("NativeTlsLocalOfferClientV91::Request(",result)
        self.assertIn("NativeSealedGrantInboxV84 temporary_inbox;",result)
        self.assertIn("TransferVerifiedTo(",result)
        self.assertIn("nat_tls_request_active_v93.test_and_set(",result)
        # A blocking TLS call MUST run outside native_grant_mutex, which
        # the ORIGINAL game UDP receive thread also uses for signed SHN1.
        call=result.index("if(!SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV91::Request(")
        before=result[:call].rfind("std::lock_guard lock(native_grant_mutex);")
        self.assertNotIn("std::lock_guard lock(native_grant_mutex);",result[before:call])
        self.assertIn("std::lock_guard lock(native_grant_mutex);",result[call:])
        self.assertIn("nat_paired_tls_generation_v92!=generation",result)
        self.assertIn("nat_paired_tls_binding_v92!=grant->pair_binding",result)
        self.assertIn("TryStartSameSocketNatProbeForTest(",result)
        self.assertIn("SameSocketNatProbeVerifiedForTest(",result)
        self.assertIn("ReceiveNativeSignedProbeV92(",result)
        # Completion must not call Reply first: a valid ReadyAck has one
        # sequence and a double-open would reject it as a replay.
        self.assertIn("NatProbeKindV91::ReadyAck",result)
        self.assertIn("nat_probe_v92->Complete(",result)
        self.assertLess(result.index("NatProbeKindV91::ReadyAck"),
                        result.index("nat_probe_v92->Complete("))
        self.assertIn("::recvfrom(host_socket",result)
        self.assertIn("Transmit(destination",result)
        self.assertNotIn("::socket(AF_INET",result)
        self.assertNotIn("SendFrame(",result)
        self.assertNotIn("direct_egress.Arm(",result)
        self.assertIn("shyt_link_generation_v87==nat_probe_link_generation_v92",result)
        self.assertIn("native_grant_inbox_v84.PendingForNat(now)",result)
        self.assertEqual(result.count("nat_probe_v92.reset(); // V92"),2)
        # SHN1 routing occurs strictly after existing firewall and before
        # original LinkServer relayed/guest vport processing.
        check=result.index("if(ReceiveNativeSignedProbeV92(from.sin_addr.s_addr")
        firewall=result.index('if (!FirewallAllows(from.sin_addr.s_addr')
        deliver=result.index("if (const auto server = LinkServer();",check)
        self.assertLess(firewall,check)
        self.assertLess(check,deliver)
        self.assertIn("#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS\n            // SHN1",result)
        self.assertIn("#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS\n    // V92",result)
        with self.assertRaisesRegex(ValueError,"already applied"):
            v92.patch_game(result)

    def test_source_drift_and_missing_identity_rejected(self):
        invalid=[
            SOURCE.replace("SHYT-V87-TRUSTED-SERVER-LINK","missing"),
            SOURCE.replace("shyt_link_generation_v87","missing"),
            SOURCE.replace("NativeSealedGrantInboxV84","NativeSealedGrantInboxV82"),
            SOURCE.replace("V86 logout/sockets closed","V80 stop"),
            SOURCE.replace("V86 account/server change","V80 relink"),
            SOURCE.replace("void ReceiveMain()","void ReceiveGame()"),
            SOURCE.replace("P2PTransport() = default;","P2PTransport() noexcept = default;"),
            SOURCE.replace('if (const auto server = LinkServer();',
                           'if (auto server = LinkServer();'),
        ]
        for x in invalid:
            with self.subTest(index=invalid.index(x)):
                with self.assertRaises(ValueError):
                    v92.patch_game(x)
if __name__=="__main__":
    unittest.main()
