// SPDX-License-Identifier: GPL-3.0-or-later
// Experimental BBHost DIRECT-UDP vs RELAY-FRAMED transport audit.
// This is actual sendto-route accounting, not a synthetic benchmark, NAT
// success claim, gameplay FPS, RTT estimate or YT seamless netcode.
// OFF unless SHYT_ROUTE_AUDIT=1. No IP addresses, IDs, tokens, payloads.
#pragma once
#include "log.h"
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

struct ShytRouteCountersV13 {
    std::atomic<std::uint64_t> direct_packets{0}, relay_packets{0};
    std::atomic<std::uint64_t> direct_wire_bytes{0}, relay_wire_bytes{0};
    std::atomic<std::uint64_t> all_packets{0};
    // V19: game-header-recognized incoming UDP datagrams queued for the game.
    // Wire bytes include the 4-byte relay-to-client prefix when present.
    // Excludes STUN, hole-punch probes, and unrecognized/no-header datagrams.
    std::atomic<std::uint64_t> direct_rx_packets{0}, relay_rx_packets{0};
    std::atomic<std::uint64_t> direct_rx_wire_bytes{0}, relay_rx_wire_bytes{0};
    std::atomic<std::uint64_t> rx_all_packets{0};
};
inline ShytRouteCountersV13 shyt_route_v13;

inline bool shyt_route_audit_enabled_v13() {
    static const bool enabled = [] {
#if defined(_WIN32)
        // The MSVC CRT deprecates getenv (C4996), which becomes a hard
        // error under clang++ -Werror. Use Win32's read-only OS API.
        char value[3] = {};
        return GetEnvironmentVariableA("SHYT_ROUTE_AUDIT", value,
                                       sizeof(value)) == 1 && value[0] == '1';
#else
        const char* value = std::getenv("SHYT_ROUTE_AUDIT");
        return value && value[0] == '1' && value[1] == '\0';
#endif
    }();
    return enabled;
}

inline void shyt_route_account_success_v13(bool framed_relay, std::uint64_t bytes_sent_on_socket) {
    if (!shyt_route_audit_enabled_v13()) return;
    // Only the successful actual P2P socket's outgoing bytes (including
    // relay framing where it was used). No failed sends, STUN probes or HTTP.
    auto& packets = framed_relay ? shyt_route_v13.relay_packets : shyt_route_v13.direct_packets;
    auto& bytes = framed_relay ? shyt_route_v13.relay_wire_bytes : shyt_route_v13.direct_wire_bytes;
    packets.fetch_add(1, std::memory_order_relaxed);
    bytes.fetch_add(bytes_sent_on_socket, std::memory_order_relaxed);
    const auto count = shyt_route_v13.all_packets.fetch_add(1, std::memory_order_relaxed)+1;
    if (count % 1024u != 0u) return;
    // Aggregate local diagnostic only. Relay-selected is not proof
    // that traffic reached a peer; direct-selected is not proof of a
    // successful NAT hole punch. The two-PC test is still mandatory.
    host_log("shyt-route-v13: sends %llu direct %llu/%llu B relay-framed %llu/%llu B (not confirmed peer delivery)",
        static_cast<unsigned long long>(count),
        static_cast<unsigned long long>(shyt_route_v13.direct_packets.load(std::memory_order_relaxed)),
        static_cast<unsigned long long>(shyt_route_v13.direct_wire_bytes.load(std::memory_order_relaxed)),
        static_cast<unsigned long long>(shyt_route_v13.relay_packets.load(std::memory_order_relaxed)),
        static_cast<unsigned long long>(shyt_route_v13.relay_wire_bytes.load(std::memory_order_relaxed)));
}

inline void shyt_route_account_received_v19(bool framed_relay,
                                           std::uint64_t bytes_received_on_socket) {
    if (!shyt_route_audit_enabled_v13()) return;
    auto& packets = framed_relay ? shyt_route_v13.relay_rx_packets : shyt_route_v13.direct_rx_packets;
    auto& bytes = framed_relay ? shyt_route_v13.relay_rx_wire_bytes : shyt_route_v13.direct_rx_wire_bytes;
    packets.fetch_add(1, std::memory_order_relaxed);
    bytes.fetch_add(bytes_received_on_socket, std::memory_order_relaxed);
    const auto count = shyt_route_v13.rx_all_packets.fetch_add(1, std::memory_order_relaxed) + 1;
    if (count % 1024u) return;
    host_log("shyt-route-v19: queued game-header receives %llu direct %llu/%llu B relay-framed %llu/%llu B (NOT proof of YT authenticated sessions)",
        static_cast<unsigned long long>(count),
        static_cast<unsigned long long>(shyt_route_v13.direct_rx_packets.load(std::memory_order_relaxed)),
        static_cast<unsigned long long>(shyt_route_v13.direct_rx_wire_bytes.load(std::memory_order_relaxed)),
        static_cast<unsigned long long>(shyt_route_v13.relay_rx_packets.load(std::memory_order_relaxed)),
        static_cast<unsigned long long>(shyt_route_v13.relay_rx_wire_bytes.load(std::memory_order_relaxed)));
}
