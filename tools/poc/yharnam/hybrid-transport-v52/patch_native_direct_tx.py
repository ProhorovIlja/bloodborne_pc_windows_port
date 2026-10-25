#!/usr/bin/env python3
"""V71 pin-sensitive native game's SendFrame direct/relay hook.

Apply ONLY to V70-composed *complete* original game P2PTransport source.
No trusted Arm invocation exists: production/default gameplay keeps relaying.
"""
from __future__ import annotations

def one(src: str, before: str, after: str, label: str)->str:
    count=src.count(before)
    if count!=1: raise ValueError(f"V71 {label}: expected one anchor, found {count}")
    return src.replace(before,after,1)

def patch(src: str)->str:
    if "SHYT-V71-NATIVE-DIRECT-TX" in src: raise ValueError("V71 already installed")
    src=one(src,
'''#include "core/libraries/network/sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC
''',
'''#include "core/libraries/network/sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC
#include "core/libraries/network/sh_native_direct_tx.hpp" // SHYT-V71-NATIVE-DIRECT-TX
''',"native game transport header")
    src=one(src,
'''        if (const auto server = LinkServer();
            Link::RoutesThroughServer(server, dest_addr_nbo, dest_port_nbo)) {
            framed = Link::EncodeData(dest_addr_nbo, dest_port_nbo, framed);
''',
'''        if (const auto server = LinkServer();
            Link::RoutesThroughServer(server, dest_addr_nbo, dest_port_nbo)) {
            // V71: only an actual trusted, authenticated and live server
            // session can create a Direct TX slot; NONE are installed today.
            // Any missing key/probe/room/owner authority or syscall failure
            // retains the ORIGINAL frame through the existing shadNet relay.
            // Direct is attempted ONLY in the branch previously sent via
            // shadNet, never as a bypass for a server-owned packet.
            bool submitted_direct = false;
            {
                std::lock_guard direct_lock(direct_egress_mutex);
                submitted_direct = direct_egress.TrySend(
                    {dest_addr_nbo,dest_port_nbo},framed,P2PNowMs()) ==
                    SeamlessHunt::Hybrid::NativeTxStatus::DirectSubmitted;
            }
            if (submitted_direct) {
                // Submissions, not measured physical wire bytes. The
                // authenticated encoder will add SHP1 framing overhead.
                route_metrics.NoteDirectSend(framed.size());
                EmitRouteMetrics();
                return static_cast<int>(len);
            }
            framed = Link::EncodeData(dest_addr_nbo, dest_port_nbo, framed);
''',"real SendFrame whole native SHAD pre-relay guard")
    src=one(src,
'''    SeamlessHunt::Hybrid::NativeDirectReceiver direct_ingress{};
''',
'''    SeamlessHunt::Hybrid::NativeDirectReceiver direct_ingress{};
    // Zero trusted outbound slots until secure server rendezvous is built.
    std::mutex direct_egress_mutex;
    SeamlessHunt::Hybrid::NativeDirectSender direct_egress{};
''',"native TX owner")
    src=one(src,
'''            direct_ingress.RevokeAll(); // no stale grant across socket restart
        }
#endif
''',
'''            direct_ingress.RevokeAll(); // no stale grant across socket restart
        }
        {
            std::lock_guard direct_lock(direct_egress_mutex);
            direct_egress.RevokeAll();
        }
#endif
''',"server socket stop revokes TX")
    src=one(src,
'''            direct_ingress.RevokeAll(); // new server/account invalidates grants
        }
        LOG_INFO(Lib_Net, "Server link: every frame for a peer goes through the server at {:#x}:{}",
''',
'''            direct_ingress.RevokeAll(); // new server/account invalidates grants
        }
        {
            std::lock_guard direct_lock(direct_egress_mutex);
            direct_egress.RevokeAll();
        }
        LOG_INFO(Lib_Net, "Server link: every frame for a peer goes through the server at {:#x}:{}",
''',"shadNet session/account replacement revokes TX")
    return src
