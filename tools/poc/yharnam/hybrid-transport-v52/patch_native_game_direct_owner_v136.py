#!/usr/bin/env python3
"""V136 developer-only original-game Direct route ownership and revoke safety.

Apply after the V135 actual YT P2PTransport clock fix. Wire the V134
server/account-bound V91 signed NAT proof to the V71 native DirectSender only
inside an explicit SHYT_ENABLE_TEST_LOCAL_MTLS debug build and a trusted
game-worker method. NO game-level auto-activation, no user-flag authorization,
no switch of server-owned, ACK/reliable/CoopStream/RPC channels.

Critical lifetime invariant: std::optional<NatProbeProofV91> is reset during
reconnect or receipt replacement. Under direct_egress_mutex AND
native_grant_mutex, refresh the signed proof pointer on every SendFrame call
before V134 ReversePathReady; revoke the slot when the proof disappears.
This prevents a previously installed DirectSender dereferencing a freed
optional or crossing a new account's signed grant. Use exactly one lock order
native_direct_egress -> native_grant -> link/SHY2, including install.

This is a developer-gated integration, NOT public Direct, a secure X509
enrolment service or tested real WAN NAT punching.
"""
from __future__ import annotations

MARKER="SHYT-V136-NATIVE-SIGNED-DIRECT-OWNER"
INCLUDE_OLD = '#include "core/libraries/network/sh_native_shy2_grant_cutover_v106.hpp" // SHYT-SHY2-V106-TRUSTED-PAIR-GATE\n'
INCLUDE_NEW = INCLUDE_OLD+'#include "core/libraries/network/sh_signed_nat_route_v134.hpp" // '+MARKER+'\n'
MEMBER_OLD = """    SeamlessHunt::Hybrid::NativeGameAeadEgress native_shy2_egress{};"""
MEMBER_NEW = MEMBER_OLD + """
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
    // Member lifetime == original native UDP transport, not a worker stack.
    SeamlessHunt::Hybrid::SignedNatRouteLeaseV134 native_signed_route_v136{};
    std::uint64_t native_signed_generation_v136=0;
#endif"""
SEND_OLD = """                submitted_direct = direct_egress.TrySend(
                    {dest_addr_nbo,dest_port_nbo},framed,P2PAuthEpochMs()) ==
                    SeamlessHunt::Hybrid::NativeTxStatus::DirectSubmitted;"""
SEND_NEW = """#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
                // SHYT-V136-NATIVE-SIGNED-DIRECT-OWNER: Direct lock is
                // acquired FIRST, followed by the grant mutex. The proof is
                // an optional whose storage can be replaced by another TLS
                // session; never dereference a stale address after reset.
                std::lock_guard grant_lock(native_grant_mutex);
                // Account/link can change before the old grant is reset.
                // Revoke it BEFORE even one stale encrypted outgoing frame.
                bool current_link_v136=false;
                {
                    std::lock_guard link_lock(link_mutex);
                    current_link_v136=native_signed_generation_v136 &&
                        native_signed_generation_v136==shyt_link_generation_v87 &&
                        link_welcomed && link_server.addr_nbo && link_server.port_nbo;
                }
                if(native_signed_generation_v136 && !current_link_v136) {
                    direct_egress.RevokeAll();
                    native_signed_route_v136={};
                    native_signed_generation_v136=0;
                }
                if (!nat_probe_v92) {
                    direct_egress.RevokeAll();
                    native_signed_route_v136.signed_nat_proof=nullptr;
                } else if (native_signed_route_v136.signed_nat_proof) {
                    native_signed_route_v136.signed_nat_proof=&*nat_probe_v92;
                }
#endif
                submitted_direct = direct_egress.TrySend(
                    {dest_addr_nbo,dest_port_nbo},framed,P2PAuthEpochMs()) ==
                    SeamlessHunt::Hybrid::NativeTxStatus::DirectSubmitted;"""
METHOD_START = "    // SHYT-SHY2-DEV-TRUSTED-CUTOVER: a game-owned worker only.\n"
METHOD_END = "    // SHYT-SHY2-ENCRYPTED-SEND: callback for the existing verified\n"
METHOD_NEW = """    // SHYT-V136-NATIVE-SIGNED-DIRECT-OWNER: only from the trusted native
    // game worker after BOTH server-granted SHG2, signed same-socket NAT,
    // authenticated game link and live map/role/consent checks. Runtime
    // game flags and network packets are NEVER allowed to invoke this.
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
    bool TryInstallVerifiedShy2ForTest(
        std::string_view local_native_sender,
        std::string_view remote_native_sender,
        SeamlessHunt::Hybrid::CurrentWorld current_world,
        void* stable_game_world, std::uint64_t now_ms) {
        const auto actual_ms=P2PAuthEpochMs();
        if(!running.load(std::memory_order_acquire) || LinkCut() ||
           actual_ms<=0 || !now_ms || !current_world ||
           !stable_game_world || now_ms>static_cast<std::uint64_t>(actual_ms)+2000 ||
           static_cast<std::uint64_t>(actual_ms)>now_ms+2000)
            return false;
        // Always direct -> grant -> link/SHY2. SendFrame takes direct then
        // grant as well. Native TLS exchange NEVER takes the direct mutex.
        std::lock_guard direct_lock(direct_egress_mutex);
        std::lock_guard grant_lock(native_grant_mutex);
        if(!nat_probe_v92)return false;
        std::uint64_t generation=0;
        std::string welcomed_id;
        {
            std::lock_guard link_lock(link_mutex);
            if(link_welcomed && link_server.addr_nbo && link_server.port_nbo &&
               shyt_link_generation_v87)
                generation=shyt_link_generation_v87;
            welcomed_id=link_online_id;
        }
        if(!generation ||
           nat_probe_link_generation_v92!=generation ||
           nat_paired_tls_generation_v92!=generation ||
           !nat_paired_tls_binding_v92)
            return false;
        std::array<std::uint8_t,32> welcomed_digest{};
        const bool identified=
            SeamlessHunt::Hybrid::NativeGameSelfIdentityV87::Digest(
                welcomed_id,welcomed_digest);
        std::fill(welcomed_id.begin(),welcomed_id.end(),char(0));
        if(!identified)return false;
        const auto* offer=native_grant_inbox_v84.PendingForNat(now_ms);
        if(!offer || offer->pair_binding!=nat_paired_tls_binding_v92 ||
           !SeamlessHunt::Hybrid::SecureOfferV84Detail::EqualDigest(
                offer->recipient_account,welcomed_digest) ||
           !nat_probe_v92->VerifiedFor(*offer,now_ms)) {
            SeamlessHunt::Hybrid::CryptoDetail::Erase(welcomed_digest);
            return false;
        }
        // Check the exact original link generation once more before cutover.
        {
            std::lock_guard link_lock(link_mutex);
            if(!link_welcomed || shyt_link_generation_v87!=generation ||
               !link_server.addr_nbo || !link_server.port_nbo) {
                SeamlessHunt::Hybrid::CryptoDetail::Erase(welcomed_digest);
                return false;
            }
        }
        bool installed=false;
        {
            std::lock_guard crypto_lock(native_shy2_mutex);
            installed=SeamlessHunt::Hybrid::NativeShy2GrantCutoverV106::Install(
                native_grant_inbox_v84,*nat_probe_v92,0,
                native_shy2_ingress,native_shy2_egress,
                local_native_sender,remote_native_sender,
                current_world,stable_game_world,now_ms);
        }
        if(!installed) {
            SeamlessHunt::Hybrid::CryptoDetail::Erase(welcomed_digest);
            return false;
        }
        native_signed_route_v136.verified_inbox=&native_grant_inbox_v84;
        native_signed_route_v136.signed_nat_proof=&*nat_probe_v92;
        native_signed_route_v136.refresh_world=current_world;
        native_signed_route_v136.world_ctx=stable_game_world;
        native_signed_route_v136.expected_signed_in_account=welcomed_digest;
        // Only encrypted direct UDP, never plain SHP1. Existing V71 router
        // keeps mandatory per-frame reliable/ACK eligibility and relay fallback.
        const bool armed=
            SeamlessHunt::Hybrid::SignedNatRouteLeaseV134::ArmAfterVerifiedCrypto(
                direct_egress,0,native_signed_route_v136,local_native_sender,
                welcomed_digest,TransmitVerifiedShy2,this,
                static_cast<std::int64_t>(now_ms));
        SeamlessHunt::Hybrid::CryptoDetail::Erase(welcomed_digest);
        if(armed) native_signed_generation_v136=generation;
        if(!armed) {
            std::lock_guard crypto_lock(native_shy2_mutex);
            native_shy2_ingress.Revoke(0);
            native_shy2_egress.Revoke(0);
            native_signed_route_v136={};
            native_signed_generation_v136=0;
        }
        return armed;
    }
#endif

"""
REVOKE_OLD = """            direct_egress.RevokeAll();
        }
"""
REVOKE_NEW = """            direct_egress.RevokeAll();
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
            native_signed_route_v136={}; // clear signed-in ID and proof refs
            native_signed_generation_v136=0; // zero old link generation
#endif
        }
"""


def one(src: str, before: str, after: str, name: str) -> str:
    if src.count(before)!=1:
        raise ValueError(f"V136 native original transport source drift: {name}")
    return src.replace(before, after, 1)


def patch_game(src: str) -> str:
    if MARKER in src:
        raise ValueError("V136 already staged")
    for fragment in ("SHYT-V135-NATIVE-AUTH-UTC-CLOCK",
                     "SHYT-V87-TRUSTED-SERVER-LINK",
                     "SHYT-V92-ORIGINAL-SOCKET-SIGNED-PROBE",
                     "SHYT-SHY2-DEV-TRUSTED-CUTOVER",
                     "native_shy2_egress.Seal(",
                     "direct_egress.TrySend(", "nat_probe_v92.reset()"):
        if fragment not in src:
            raise ValueError("V136 missing pinned native runtime stage: "+fragment)
    src=one(src,INCLUDE_OLD,INCLUDE_NEW,"encrypted crypto include")
    src=one(src,MEMBER_OLD,MEMBER_NEW,"native AES slots owner")
    src=one(src,SEND_OLD,SEND_NEW,"original game SendFrame direct->grant locking")
    if src.count(METHOD_START)!=1 or src.count(METHOD_END)!=1:
        raise ValueError("V136 missing original game crypto-only debug worker")
    begin=src.index(METHOD_START)
    end=src.index(METHOD_END,begin)
    old=src[begin:end]
    if "NativeShy2GrantCutoverV106::Install(" not in old or \
       "std::lock_guard grant_lock(native_grant_mutex);" not in old or \
       "native_shy2_egress" not in old or \
       "direct_egress.Arm(" in old:
        raise ValueError("V136 predecessor debug install unexpectedly changed")
    src=src[:begin]+METHOD_NEW+src[end:]
    if src.count(REVOKE_OLD)!=2:
        raise ValueError("V136 needs BOTH original native game logout/stop route revocations")
    src=src.replace(REVOKE_OLD,REVOKE_NEW)
    if src.count("SignedNatRouteLeaseV134::ArmAfterVerifiedCrypto(")!=1:
        raise ValueError("Unexpected game direct Arm outside protected debug method")
    if src.count("P2PAuthEpochMs()")!=4: # function + RX + SendFrame + debug method
        raise ValueError("Mixed or duplicate native security clock")
    if src.count("#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS")<4:
        raise ValueError("Missing developer flag security")
    return src
