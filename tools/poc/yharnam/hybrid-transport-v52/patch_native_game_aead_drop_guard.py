#!/usr/bin/env python3
"""SHY2 AES-GCM ingress in the ORIGINAL Bloodborne native recvfrom socket.

No inbound peer is armed by this patch, so production behavior remains
SHLK relay. A future server-authenticated and mutually proven rendezvous
must explicitly install each AES-GCM pair/physical/virtual/world slot.
Reliable GameLink ACKs and server-owned channels are NEVER direct.
"""
from __future__ import annotations

NETWORK = "emulator/src/core/libraries/network/p2p_sockets.cpp"
AEAD_HEADER = "emulator/src/core/libraries/network/sh_native_game_aead.hpp"
INGRESS_HEADER = "emulator/src/core/libraries/network/sh_native_game_aead_ingress.hpp"
EGRESS_HEADER = "emulator/src/core/libraries/network/sh_native_game_aead_egress.hpp"
CUTOVER_HEADER = "emulator/src/core/libraries/network/sh_native_shy2_grant_cutover_v106.hpp"
TAG = "SHYT-SHY2-AUTHENTICATED-INGRESS"


def one(src: str, before: str, after: str, label: str) -> str:
    n = src.count(before)
    if n != 1:
        raise ValueError(f"SHY2 {label}: {n} pinned anchors")
    return src.replace(before, after, 1)


def patch_game(src: str) -> str:
    if TAG in src:
        raise ValueError("SHY2 original-game ingress already installed")
    for expected in ("SHYT-V70-NATIVE-RECV-HMAC", "direct_ingress.RevokeAll()",
                     "direct_egress.RevokeAll()", "SHYT-V87-TRUSTED-SERVER-LINK"):
        if expected not in src:
            raise ValueError("SHY2 missing original game secure route: " + expected)
    src = one(src,
        '#include "core/libraries/network/sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC\n',
        '#include "core/libraries/network/sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC\n'
        '#include "core/libraries/network/sh_native_game_aead_ingress.hpp" // ' + TAG + '\n'
        '#include "core/libraries/network/sh_native_game_aead_egress.hpp" // SHYT-SHY2-AUTHENTICATED-EGRESS\n'
        '#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS\n'
        '#include "core/libraries/network/sh_native_shy2_grant_cutover_v106.hpp" // SHYT-SHY2-V106-TRUSTED-PAIR-GATE\n'
        '#endif\n',
        "actual game header")
    src = one(src,
        '    SeamlessHunt::Hybrid::NativeDirectReceiver direct_ingress{};\n',
        '    SeamlessHunt::Hybrid::NativeDirectReceiver direct_ingress{};\n'
        '    // No SHY2 Arm installer exists. Every unknown encrypted datagram is dropped.\n'
        '    std::mutex native_shy2_mutex;\n'
        '    SeamlessHunt::Hybrid::NativeGameAeadIngress native_shy2_ingress{};\n'
        '    SeamlessHunt::Hybrid::NativeGameAeadEgress native_shy2_egress{};\n',
        "actual game crypto slot owner")
    marker = """            if (SeamlessHunt::Hybrid::IsSHP1(datagram)) {
                SeamlessHunt::Hybrid::NativeRxResult verified{};"""
    ingress = """            // SHYT-SHY2-ENCRYPTED-GAME-UDP: recognize encrypted peer
            // datagrams on this SAME original host_socket only. A real,
            // fresh, authenticated server pair slot is mandatory. Unarmed,
            // forged, stale, wrong-world and reliable frames are consumed.
            // Never permit SHY2 to fall through as SHLK or raw game bytes.
            if (SeamlessHunt::Hybrid::IsSHY2(datagram)) {
                SeamlessHunt::Hybrid::NativeShy2Result verified{};
                {
                    std::lock_guard shy2_lock(native_shy2_mutex);
                    verified = native_shy2_ingress.Receive(
                        {from.sin_addr.s_addr,from.sin_port},datagram,P2PNowMs());
                }
                if (verified.status==SeamlessHunt::Hybrid::NativeRxStatus::Game) {
                    route_metrics.NoteDirectReceive(datagram.size());
                    Deliver(verified.sender.addr_nbo,verified.sender.port_nbo,
                            verified.native_game_frame);
                }
                continue;
            }
"""
    src = one(src, marker, ingress + marker, "original recvfrom demux")
    # The ORIGINAL native game already calls NativeDirectSender::TrySend()
    # in SendFrame, which owns verified reverse NAT, authority, and relay
    # fallback. Supply a real SHY2 AES-GCM same-socket writer callback,
    # but NEVER call native Direct Arm without live server authorization.
    callback = """    // SHYT-SHY2-ENCRYPTED-SEND: callback for the existing verified
    // NativeDirectSender only. No code currently installs/arms this.
    // Seals the whole native frame with a server-issued directional key,
    // then transmits over the game's ORIGINAL host_socket via Transmit().
    // Any crypto, key expiry or socket failure returns to normal SHLK relay.
    static bool TransmitVerifiedShy2(
        SeamlessHunt::Hybrid::PhysicalV4 peer,
        std::span<const std::uint8_t> complete_frame,
        std::int64_t now_ms,void* trusted_transport) noexcept {
        if(!trusted_transport)return false;
        auto* self=static_cast<P2PTransport*>(trusted_transport);
        try {
            std::vector<u8> sealed;
            {
                std::lock_guard shy2_lock(self->native_shy2_mutex);
                if(!self->native_shy2_egress.Seal(
                       peer,complete_frame,now_ms,sealed))
                    return false;
            }
            sockaddr_in dest{};
            dest.sin_family=AF_INET;
            dest.sin_addr.s_addr=peer.addr_nbo;
            dest.sin_port=peer.port_nbo;
            return self->Transmit(dest,std::move(sealed));
        } catch(...) {
            return false; // no C++ exception across native game TX callback
        }
    }

"""
    src = one(src,
        '    static bool TrustedReverseDirectReady(\n',
        method + callback + '    static bool TrustedReverseDirectReady(\n',
        "original game verified sender callback")
    # V71 has TWO independent lifecycle revocations. The encrypted route
    # requires both; no stale AES peer may survive logout/server swap/stop.
    old = """            direct_egress.RevokeAll();
        }
"""
    if src.count(old) != 2:
        raise ValueError("SHY2 missing both original game revoke paths")
    src = src.replace(old,
        old + """        {
            std::lock_guard shy2_lock(native_shy2_mutex);
            native_shy2_ingress.RevokeAll(); // revoke AES peer keys on stop/swap
            native_shy2_egress.RevokeAll(); // matching outbound AES lease
        }
""")
    return src
