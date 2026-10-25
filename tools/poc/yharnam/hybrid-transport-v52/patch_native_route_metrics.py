#!/usr/bin/env python3
"""V69 opt-in route telemetry in REAL original P2PTransport, not test-only.

Applied to V7-composed native Yharnam Together p2p_sockets.cpp.
All source anchors are checked atomically. No P2P grant or socket change.
"""
from pathlib import Path
NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="emulator/src/core/libraries/network/sh_route_metrics.hpp"

def one(source, old, new, label):
    count=source.count(old)
    if count!=1: raise ValueError(f"V69 {label}: expected exact anchor, found {count}")
    return source.replace(old,new,1)

def patch(source: str)->str:
    if "SHYT_ROUTE_METRICS" in source:
        raise ValueError("route telemetry already applied")
    source=one(source,
'''#include "net_error.h"
''',
'''#include "net_error.h"
#include "core/libraries/network/sh_route_metrics.hpp" // V69
''',"native transport include")
    source=one(source,
'''        physical_port = ntohs(actual.sin_port);
        running.store(true, std::memory_order_release);
''',
'''        physical_port = ntohs(actual.sin_port);
        // Opt-in only: 0 allocations or per-packet logging, no real IP/user data.
        if (const char* metric = std::getenv("SHYT_ROUTE_METRICS");
            metric && std::strcmp(metric, "1") == 0) {
            route_metrics.SetEnabled(true);
        }
        running.store(true, std::memory_order_release);
''',"native game socket startup")
    source=one(source,
'''        // The server link: the frame goes to shadNet, which hands it to the peer.
        if (const auto server = LinkServer();
            Link::RoutesThroughServer(server, dest_addr_nbo, dest_port_nbo)) {
            framed = Link::EncodeData(dest_addr_nbo, dest_port_nbo, framed);
            dest.sin_addr.s_addr = server.addr_nbo;
            dest.sin_port = server.port_nbo;
        }
        return Transmit(dest, std::move(framed)) ? static_cast<int>(len) : -1;
''',
'''        // V69 real-game route accounting: count only frames successfully
        // submitted to native transport (including delayed / simulated loss).
        // No routing or packet contents are changed by this probe.
        bool via_shadnet = false;
        const bool native_game = SeamlessHunt::Hybrid::IsNativeShadGamePacket(
            framed.data(), framed.size());
        // The server link: the frame goes to shadNet, which hands it to the peer.
        if (const auto server = LinkServer();
            Link::RoutesThroughServer(server, dest_addr_nbo, dest_port_nbo)) {
            framed = Link::EncodeData(dest_addr_nbo, dest_port_nbo, framed);
            dest.sin_addr.s_addr = server.addr_nbo;
            dest.sin_port = server.port_nbo;
            via_shadnet = true;
        }
        const auto submitted_bytes = framed.size();
        const bool submitted = Transmit(dest, std::move(framed));
        if (submitted) {
            if (via_shadnet)
                route_metrics.NoteServerSend(submitted_bytes, native_game);
            else
                route_metrics.NoteDirectSend(submitted_bytes);
        } else {
            route_metrics.NoteSendFailure();
        }
        EmitRouteMetrics();
        return submitted ? static_cast<int>(len) : -1;
''',"actual SendFrame via shadNet")
    source=one(source,
'''    void ConfigureLink(u32 server_addr_nbo, u16 server_port_nbo, std::string online_id,
''',
'''    void EmitRouteMetrics() {
        if (!route_metrics.ShouldEmit(P2PNowMs())) return;
        const auto stats = route_metrics.Snapshot();
        LOG_INFO(Lib_Net,
                 "YT network submitted: relay_out={} packets / {} bytes; "
                 "relay_game_out={} packets / {} bytes; relay_in={} packets / {} bytes; "
                 "native_direct_out={} packets / {} bytes; "
                 "native_direct_in={} packets / {} bytes; tx_failures={}",
                 stats.relay_out_packets, stats.relay_out_bytes,
                 stats.relay_out_game_packets, stats.relay_out_game_bytes,
                 stats.relay_in_packets, stats.relay_in_bytes,
                 stats.native_direct_out_packets, stats.native_direct_out_bytes,
                 stats.native_direct_in_packets, stats.native_direct_in_bytes,
                 stats.send_failures);
    }

    void ConfigureLink(u32 server_addr_nbo, u16 server_port_nbo, std::string online_id,
''',"throttled game metrics logger")
    source=one(source,
'''        case Link::Kind::Data:
            if (const auto data = Link::DecodeData(datagram)) {
                Deliver(data->addr_nbo, data->port_nbo, data->frame);
            }
            return;
''',
'''        case Link::Kind::Data:
            if (const auto data = Link::DecodeData(datagram)) {
                route_metrics.NoteRelayReceive(datagram.size());
                Deliver(data->addr_nbo, data->port_nbo, data->frame);
                EmitRouteMetrics();
            }
            return;
''',"actual server-relayed receive")
    source=one(source,
'''    net_socket host_socket{kInvalidSocket};
''',
'''    SeamlessHunt::Hybrid::RouteMetrics route_metrics{}; // V69 disabled by default
    net_socket host_socket{kInvalidSocket};
''',"physical socket counters")
    return source

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("checkout",type=Path)
    args=p.parse_args()
    target=args.checkout/NETWORK
    original=target.read_text("utf-8")
    transformed=patch(original)
    target.write_text(transformed,"utf-8")
    header=args.checkout/HEADER
    if not header.is_file():
        raise SystemExit(f"missing telemetry header in composed checkout: {header}")
    print("SHYT_V69_NATIVE_P2P_SEND_RELAY_METRICS_PASS")
