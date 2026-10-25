#!/usr/bin/env python3
"""V70 actual Yharnam Together physical UDP recvfrom() SHA/HMAC demux hook.

Apply only AFTER V69 to a full pinned native composed source. A server-signed,
encrypted control-plane installer is still missing; no native caller ever
arms NativeDirectReceiver, so SHP1 packets are always rejected by default.
"""
from __future__ import annotations

NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
DIRECT_HEADERS=(
    "sh_native_direct_rx.hpp",
    "sh_direct_ingress.hpp",
    "sh_direct_datagram.hpp",
    "sh_game_frame_offload.hpp",
    "sh_channel_offload.hpp",
    "sh_hybrid_selector.hpp",
)

def one(text: str, old: str, new: str, label: str) -> str:
    n=text.count(old)
    if n!=1: raise ValueError(f"V70 {label}: expected 1 pinned source anchor, got {n}")
    return text.replace(old,new,1)

def patch(src: str) -> str:
    if "SHYT-V70-NATIVE-RECV-HMAC" in src:
        raise ValueError("V70 already applied")
    src=one(src,
'''#include "core/libraries/network/sh_route_metrics.hpp" // V69
''',
'''#include "core/libraries/network/sh_route_metrics.hpp" // V69
#include "core/libraries/network/sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC
''',"native shared socket header")
    src=one(src,
'''            if (!Link::TakesDatagramFrom(LinkServer(), from.sin_addr.s_addr, from.sin_port)) {
''',
'''            // SHYT-V70-NATIVE-RECV-HMAC: the existing real recvfrom() host
            // socket receives both SHLK relay and future SHP1 peer datagrams.
            // Only server-authenticated MAC + peer candidate + current world
            // authority may recover the signed VIRTUAL source for Deliver().
            // Until a trustworthy control-plane installer is implemented,
            // direct_ingress is empty and drops ALL SHP1 (never falls through).
            if (SeamlessHunt::Hybrid::IsSHP1(datagram)) {
                SeamlessHunt::Hybrid::NativeRxResult verified{};
                {
                    std::lock_guard direct_lock(direct_ingress_mutex);
                    verified = direct_ingress.Receive(
                        {from.sin_addr.s_addr,from.sin_port}, datagram, P2PNowMs());
                }
                if (verified.status == SeamlessHunt::Hybrid::NativeRxStatus::Game) {
                    route_metrics.NoteDirectReceive(datagram.size());
                    Deliver(verified.sender.addr_nbo,verified.sender.port_nbo,
                            verified.native_game_frame);
                }
                continue; // MAC-invalid/unknown peer must never use legacy delivery
            }
            if (!Link::TakesDatagramFrom(LinkServer(), from.sin_addr.s_addr, from.sin_port)) {
''',"native recvfrom demux after official server SHLK")
    src=one(src,
'''    SeamlessHunt::Hybrid::RouteMetrics route_metrics{}; // V69 disabled by default
''',
'''    SeamlessHunt::Hybrid::RouteMetrics route_metrics{}; // V69 disabled by default
    // V70: no control-plane Arm call exists; P2P is DENIED by default.
    // Any future Arm/Revoke must be synchronized against ReceiveMain.
    std::mutex direct_ingress_mutex;
    SeamlessHunt::Hybrid::NativeDirectReceiver direct_ingress{};
''',"actual socket candidate state")
    src=one(src,
'''        physical_port = 0;
#endif
    }

    bool IsReady() const {
''',
'''        physical_port = 0;
        {
            std::lock_guard direct_lock(direct_ingress_mutex);
            direct_ingress.RevokeAll(); // no stale grant across socket restart
        }
#endif
    }

    bool IsReady() const {
''',"revocation on native socket stop")
    src=one(src,
'''        LOG_INFO(Lib_Net, "Server link: every frame for a peer goes through the server at {:#x}:{}",
''',
'''        {
            std::lock_guard direct_lock(direct_ingress_mutex);
            direct_ingress.RevokeAll(); // new server/account invalidates grants
        }
        LOG_INFO(Lib_Net, "Server link: every frame for a peer goes through the server at {:#x}:{}",
''',"revocation on server link reconfigure")
    return src
