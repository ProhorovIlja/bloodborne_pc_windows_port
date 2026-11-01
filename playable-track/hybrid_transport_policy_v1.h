// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// SHYT playable-track prototype: fail-closed per-packet transport selection.
//
// This is a PURE policy shim against upstream Yharnam Together's public
// coop/packet_routes.h, not a shipping multiplayer transport integration.
// Until both the GAME and the SERVER negotiate an authenticated direct
// route and share one sequence/deduplication domain, DO NOT enable it.
//
// The original upstream code/server remains the source of truth for map,
// enemy owner and reliable stream semantics. Never bypass server-authoritative
// world logs, matchmaking, team management, invasion rules or imports.
// Only native UNRELIABLE CHANNEL 0x06 (player movement) is eligible in v1.
// No direct packets are ever sent under uncertainty.
#include <cstdint>
#include <string_view>
#include "coop/packet_routes.h"

namespace BloodborneCoop::SHYTHybrid {

enum class Carrier : u8 { Drop = 0, Server = 1, DirectPeer = 2 };

struct PeerRouteLease {
    // All are established on the authoritative server's authenticated link,
    // never on unauthenticated peer UDP discovery alone.
    bool local_opt_in = false;
    bool remote_opt_in = false;
    bool same_party_session = false;
    bool session_authenticated = false;
    bool peer_authenticated = false;
    bool direct_datagram_verified = false;
    bool server_route_granted = false;
    bool sender_or_receiver_hostile = false;
    bool has_common_protocol = false;

    // Server-issued grant MUST identify the exact ordered pair of hunters.
    // Views refer to authenticated session-owned, lifetime-stable IDs.
    // A valid lease for hunter A -> B cannot authorize C -> B or A -> C.
    std::string_view granted_sender_id{};
    std::string_view granted_receiver_id{};

    // Server grants only a specific sender/receiver and map, for the
    // current party-world epoch. Rejoin/load/teleport revokes the lease.
    u64 authority_epoch = 0;
    u64 local_world_epoch = 0;
    u32 approved_sender_map = 0;
    u32 approved_target_map = 0;
    s64 now_ms = 0;
    s64 lease_expiry_ms = 0;
    s64 last_authenticated_direct_probe_ms = -1;
    static constexpr s64 ProbeFreshMs = 2500;
};

// The game MUST continue using the same native sequence number stream for
// both server relays and direct peer packets. Receiver MUST deduplicate by
// {sender, instance, channel, sequence} regardless of carrier. Switching
// carriers must not alter reliable packet semantics (they remain on server).
constexpr Carrier ChooseNativePacketCarrier(
    u32 channel, const PacketEnds& ends, const PeerRouteLease& link)
{
    // Original YT authoritative per-map/owner channel rules are always first.
    // This is not an alternative routing table.
    if (!RoutesNativePacket(channel, ends)) return Carrier::Drop;

    // Only 0x06: the native game's UNRELIABLE player movement channel.
    // Enemy position/HP, boss, hit, inventory, flags, character, all
    // reliable packets, party RPC and world-log protobuf stay on SERVER.
    if (channel != 0x06 || IsReliableNativeChannel(channel))
        return Carrier::Server;

    if (!link.local_opt_in || !link.remote_opt_in ||
        !link.same_party_session || !link.session_authenticated ||
        !link.peer_authenticated || !link.direct_datagram_verified ||
        !link.server_route_granted || link.sender_or_receiver_hostile ||
        !link.has_common_protocol || link.granted_sender_id.empty() ||
        link.granted_receiver_id.empty())
        return Carrier::Server;

    if (!link.authority_epoch ||
        link.authority_epoch != link.local_world_epoch ||
        !ends.sender_map || !ends.target_map ||
        ends.sender_map != ends.target_map ||
        link.approved_sender_map != ends.sender_map ||
        link.approved_target_map != ends.target_map)
        return Carrier::Server;

    // An expired lease, a stale probe or a future-dated probe fails closed.
    // Subtraction is protected by ordering to avoid signed overflow.
    if (link.now_ms < 0 || link.lease_expiry_ms <= link.now_ms ||
        link.last_authenticated_direct_probe_ms < 0 ||
        link.now_ms < link.last_authenticated_direct_probe_ms ||
        link.now_ms - link.last_authenticated_direct_probe_ms > PeerRouteLease::ProbeFreshMs)
        return Carrier::Server;

    return Carrier::DirectPeer;
}
} // namespace BloodborneCoop::SHYTHybrid
