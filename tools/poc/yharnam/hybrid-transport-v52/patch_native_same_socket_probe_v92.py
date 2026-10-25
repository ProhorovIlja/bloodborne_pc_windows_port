#!/usr/bin/env python3
"""V92 native Yharnam Together ORIGINAL P2PTransport same-socket NAT probes.

Developer-flag gated. Uses original receive thread's recvfrom, exact
server-authenticated peer endpoint, original firewall, original LinkWelcomed
generation and original host_socket's Transmit. ZERO effect on normal game
datagrams, GameLink or live Direct routing. Caller-controlled flags do not
authorize game routing. No additional UDP socket is created.
"""
from __future__ import annotations
NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="emulator/src/core/libraries/network/sh_nat_probe_v91.hpp"
TAG="SHYT-V92-ORIGINAL-SOCKET-SIGNED-PROBE"

def one(s,old,new,what):
    n=s.count(old)
    if n!=1:
        raise ValueError(f"V92 {what}: expected exact one pinned source anchor, got {n}")
    return s.replace(old,new,1)

def patch_game(src):
    if TAG in src:raise ValueError("V92 already applied")
    if ("SHYT-V87-TRUSTED-SERVER-LINK" not in src or
        "native_grant_inbox_v84" not in src or
        "shyt_link_generation_v87" not in src):
        raise ValueError("V92 requires original game and V84-V87 verified integration")
    src=one(src,
        '#include "core/libraries/network/sh_native_game_identity_v87.hpp" // SHYT-V87-TRUSTED-SERVER-LINK\n',
        '#include "core/libraries/network/sh_native_game_identity_v87.hpp" // SHYT-V87-TRUSTED-SERVER-LINK\n'
        '#include "core/libraries/network/sh_nat_probe_v91.hpp" // '+TAG+'\n'
        '#include "core/libraries/network/sh_native_tls_local_client_v91.hpp" // V92 paired TLS-only admission\n',
        "dev-only native probe header")
    src=one(src,
        '    SeamlessHunt::Hybrid::NativeSealedGrantInboxV84 native_grant_inbox_v84{};\n',
        '    SeamlessHunt::Hybrid::NativeSealedGrantInboxV84 native_grant_inbox_v84{};\n'
        '    std::optional<SeamlessHunt::Hybrid::NatProbeProofV91> nat_probe_v92;\n'
        '    std::uint64_t nat_probe_link_generation_v92=0;\n'
        '    std::uint64_t nat_paired_tls_generation_v92=0;\n'
        '    std::uint64_t nat_paired_tls_binding_v92=0;\n'
        '    std::atomic_flag nat_tls_request_active_v93=ATOMIC_FLAG_INIT;\n',
        "existing full-identity native grant member")
    for old,remark in (
        ('            native_grant_inbox_v84.Revoke(); // V86 logout/sockets closed\n',"socket shutdown"),
        ('            native_grant_inbox_v84.Revoke(); // V86 account/server change\n',"account/server change"),
    ):
        src=one(src,old,old+
            '            nat_probe_v92.reset(); // V92 '+remark+', wipe probe secrets\n'
            '            nat_probe_link_generation_v92=0;\n'
            '            nat_paired_tls_generation_v92=0;\n'
            '            nat_paired_tls_binding_v92=0;\n',
            remark+" revocation")
    method='''    // V92: ONLY a full SHG2 *coordinated* V90 pair can probe. The
    // original game's authenticated online ID must agree with the
    // certificate identity and must survive the entire blocking mTLS
    // handshake. V85 standalone SHG2 is explicitly NOT sufficient.
    bool TryPairedTlsReadyForNatTest(
        const SeamlessHunt::Hybrid::NativeTlsLocalConfig& cfg,
        const SeamlessHunt::Hybrid::NativeOfferIdentityV84& expected,
        std::uint64_t serial,
        SeamlessHunt::Hybrid::RefreshNativeOfferIdentityV84 current,
        void* verified_game_state,std::uint64_t now_ms,bool& both_ready) {
        both_ready=false;
        if(nat_tls_request_active_v93.test_and_set(
              std::memory_order_acquire))return false;
        struct ClearBusyV93 {
            std::atomic_flag& busy;
            ~ClearBusyV93(){busy.clear(std::memory_order_release);}
        } clear_busy{nat_tls_request_active_v93};
        if(!running.load(std::memory_order_acquire) || LinkCut())
            return false;
        std::uint64_t generation=0;
        std::string game_id;
        bool welcomed=false,configured=false;
        {
            std::lock_guard link_lock(link_mutex);
            generation=shyt_link_generation_v87;
            game_id=link_online_id;
            welcomed=link_welcomed;
            configured=link_server.addr_nbo && link_server.port_nbo;
        }
        const bool valid=generation &&
            SeamlessHunt::Hybrid::NativeGameSelfIdentityV87::MatchesAcceptedLink(
                game_id,welcomed,configured,expected);
        std::fill(game_id.begin(),game_id.end(),char(0));
        if(!valid)return false;
        {
            std::lock_guard lock(native_grant_mutex);
            nat_probe_v92.reset();
            nat_probe_link_generation_v92=0;
            nat_paired_tls_generation_v92=0;
            nat_paired_tls_binding_v92=0;
            native_grant_inbox_v84.Revoke();
        }
        // TLS I/O must never block the game's original UDP receive path.
        SeamlessHunt::Hybrid::NativeSealedGrantInboxV84 temporary_inbox;
        bool receipt=false;
        if(!SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV91::Request(
              cfg,temporary_inbox,expected,serial,current,
              verified_game_state,now_ms,receipt))return false;
        const auto received_ms=static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
        if(!running.load(std::memory_order_acquire) || LinkCut())
            return false;
        {
            // Only short, in-memory transfer under the game grant lock.
            std::lock_guard lock(native_grant_mutex);
            std::lock_guard link_lock(link_mutex);
            if(!running.load(std::memory_order_acquire) ||
               shyt_link_generation_v87!=generation || !link_welcomed ||
               !link_server.addr_nbo || !link_server.port_nbo)
                return false;
            const auto* grant=temporary_inbox.PendingForNat(received_ms);
            if(!grant)return false;
            const auto binding=grant->pair_binding;
            if(!temporary_inbox.TransferVerifiedTo(
                  native_grant_inbox_v84,received_ms))return false;
            nat_paired_tls_generation_v92=generation;
            nat_paired_tls_binding_v92=binding;
        }
        both_ready=receipt;
        return true; // Still NOT permission for Direct game traffic
    }

    // V92 DEV-ONLY. Called from trusted native game worker, never UDP
    // receive thread. This sends only a 144-byte SIGNED challenge over
    // the existing host_socket; it NEVER changes the guest game-frame sender.
    bool TryStartSameSocketNatProbeForTest(bool initiator,std::uint64_t now_ms) {
        if(!running.load(std::memory_order_acquire) || LinkCut())
            return false;
        SeamlessHunt::Hybrid::NatProbeCodecV91::Wire initial{};
        sockaddr_in destination{};
        bool send=false;
        {
            std::lock_guard lock(native_grant_mutex);
            nat_probe_v92.reset();
            nat_probe_link_generation_v92=0;
            std::uint64_t generation=0;
            bool welcomed=false;
            {
                std::lock_guard link_lock(link_mutex);
                generation=shyt_link_generation_v87;
                welcomed=link_welcomed && link_server.addr_nbo &&
                          link_server.port_nbo;
            }
            const auto* grant=native_grant_inbox_v84.PendingForNat(now_ms);
            if(!generation || !welcomed || !grant ||
               nat_paired_tls_generation_v92!=generation ||
               nat_paired_tls_binding_v92!=grant->pair_binding)
                return false;
            nat_probe_v92.emplace(
                initiator ?
                  SeamlessHunt::Hybrid::NatProbeProofV91::Role::Initiator :
                  SeamlessHunt::Hybrid::NatProbeProofV91::Role::Responder);
            if(!nat_probe_v92->Start(*grant,now_ms)) {
                nat_probe_v92.reset();return false;
            }
            nat_probe_link_generation_v92=generation;
            if(initiator) {
                if(!nat_probe_v92->Initial(now_ms,initial)) {
                    nat_probe_v92.reset();
                    nat_probe_link_generation_v92=0;
                    return false;
                }
                destination.sin_family=AF_INET;
                destination.sin_addr.s_addr=grant->peer_ipv4_nbo;
                destination.sin_port=grant->peer_port_nbo;
                send=true;
            }
        }
        // Release grant lock before the original socket's sendto path.
        // Firewall, existing delay simulation and LinkCut still apply.
        if(send && !Transmit(destination,std::vector<u8>(
              initial.begin(),initial.end()))) {
            std::lock_guard lock(native_grant_mutex);
            nat_probe_v92.reset();
            nat_probe_link_generation_v92=0;
            return false;
        }
        return true; // NOT permission for Direct game routing
    }

    // V92 test diagnostic: valid signed challenge/response received, but
    // NO GameLink migration and no UDP gameplay authorization.
    bool SameSocketNatProbeVerifiedForTest() {
        std::lock_guard lock(native_grant_mutex);
        return nat_probe_v92 && nat_probe_v92->InitiatorVerified();
    }
'''
    # A manually invoked old V85 one-sided offer must never be permitted
    # to inherit the pair-authorized NAT socket state from an earlier V91
    # full two-recipient receipt (even if the same online ID reconnects).
    src=one(src,
        '''        const bool received=SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
''',
        '''        nat_probe_v92.reset();
        nat_probe_link_generation_v92=0;
        nat_paired_tls_generation_v92=0;
        nat_paired_tls_binding_v92=0;
        const bool received=SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
''',
        "legacy one-sided mTLS cannot inherit V92 paired-transport admission")
    src=one(src,
        '''private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(''',
        method+'''private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(''',
        "existing V83-V87 guarded public debug method")
    handle='''    // V92 uses the EXACT original receive thread and host_socket.
    // The caller has already executed LinkCut & existing firewall check.
    // Recognized signed-control prefix never goes to a guest game socket.
    bool ReceiveNativeSignedProbeV92(
        u32 source_ip_nbo,u16 source_port_nbo,
        std::span<const u8> bytes) {
        if(bytes.size()<4 || bytes[0]!='S' || bytes[1]!='H' ||
           bytes[2]!='N' || bytes[3]!='1')return false;
        SeamlessHunt::Hybrid::NatProbeCodecV91::Wire response{};
        sockaddr_in destination{};
        bool send=false;
        const auto now=static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
        {
            std::lock_guard lock(native_grant_mutex);
            bool link_ok=false;
            {
                std::lock_guard link_lock(link_mutex);
                link_ok=link_welcomed && shyt_link_generation_v87 &&
                   shyt_link_generation_v87==nat_probe_link_generation_v92 &&
                   link_server.addr_nbo && link_server.port_nbo;
            }
            const auto* grant=native_grant_inbox_v84.PendingForNat(now);
            if(!link_ok || !grant || !nat_probe_v92 ||
               nat_paired_tls_generation_v92!=nat_probe_link_generation_v92 ||
               nat_paired_tls_binding_v92!=grant->pair_binding) {
                nat_probe_v92.reset();
                nat_probe_link_generation_v92=0;
                return true; // consume only the SHN1 control prefix
            }
            // ReadyAck must go DIRECTLY to Complete(). Calling Reply()
            // first would consume its valid sequence in the one-use
            // anti-replay window and falsely reject the final proof.
            // The kind byte selects a handler, NOT an authorization:
            // both handlers verify full HMAC, IDs, candidate and nonce.
            if(bytes.size()==SeamlessHunt::Hybrid::NatProbeCodecV91::kWireBytes &&
               bytes[5]==static_cast<std::uint8_t>(
                 SeamlessHunt::Hybrid::NatProbeKindV91::ReadyAck)) {
                (void)nat_probe_v92->Complete(
                    bytes,source_ip_nbo,source_port_nbo,now);
            } else {
                send=nat_probe_v92->Reply(
                    bytes,source_ip_nbo,source_port_nbo,now,response);
            }
            if(send) {
                destination.sin_family=AF_INET;
                destination.sin_addr.s_addr=grant->peer_ipv4_nbo;
                destination.sin_port=grant->peer_port_nbo;
            }
        }
        if(send) {
            // Use the EXISTING UDP host_socket, never open a new socket.
            (void)Transmit(destination,
                std::vector<u8>(response.begin(),response.end()));
        }
        return true;
    }

'''
    src=one(src,
        '''    void ReceiveMain() {
''',
        '''#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
'''+handle+'''#endif
    void ReceiveMain() {
''',
        "original game receive helper")
    src=one(src,
        '''            const std::span<const u8> datagram{buffer.data(), static_cast<size_t>(rc)};
            if (const auto server = LinkServer();
''',
        '''            const std::span<const u8> datagram{buffer.data(), static_cast<size_t>(rc)};
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
            // SHN1 is an authenticated out-of-band control frame. It is
            // checked AFTER firewall and BEFORE the guest vport decoder.
            // With default build flag OFF this block does not even exist.
            if(ReceiveNativeSignedProbeV92(from.sin_addr.s_addr,from.sin_port,
                                           datagram))continue;
#endif
            if (const auto server = LinkServer();
''',
        "original recvfrom pre-guest callback")
    return src
