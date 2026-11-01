// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V240: real YT GameLinkPeer/GameFrame egress carrier with lossless fallback.
// This is NOT a UDP socket, NAT traversal, authentication or encryption.
// The caller MUST use the original, single GameLinkPeer::Send/Flush sequence
// domain; direct_send MUST seal the datagram to the authenticated endpoint.
// When secure direct transport is absent, this code *always* chooses server.
#include "hybrid_direct_ingress_v2.h"
#include <cstddef>
#include <cstdint>
#include <string_view>
#include <utility>

namespace BloodborneCoop::SHYTHybrid {

enum class EgressResult { Failed, Server, Direct };

struct DirectEgressIdentity {
    std::string_view server_authorized_local_id;
    std::string_view server_authorized_remote_id;
    std::string_view server_authorized_party_session_id;
    u32 local_instance = 0;
    u32 remote_instance = 0;
    bool secure_peer_datagram_sender_installed = false;
    size_t max_direct_movement_bytes = 1100;
};

inline bool IsExactUnreliableMovement(const GameFrame& frame, size_t max_bytes) {
    if (frame.entries.size() != 1) return false;
    const GameFrameEntry& entry = frame.entries[0];
    if (entry.packet_class != PacketClass::Unreliable ||
        entry.packet.size() <= 8 || entry.packet.size() > max_bytes) return false;
    const auto& p = entry.packet;
    const u32 channel = static_cast<u32>(p[0]) |
        (static_cast<u32>(p[1]) << 8) |
        (static_cast<u32>(p[2]) << 16) |
        (static_cast<u32>(p[3]) << 24);
    const u32 size = static_cast<u32>(p[4]) |
        (static_cast<u32>(p[5]) << 8) |
        (static_cast<u32>(p[6]) << 16) |
        (static_cast<u32>(p[7]) << 24);
    return channel == 0x06 && size == p.size() - 8;
}

// Callback signatures: bool secure_direct_send(GameFrame const&);
// bool existing_server_link_send(GameFrame const&).
// Only the original GameFrame is used on fallback. In particular its
// GameLinkPeer sequence, sender and peer instance are NEVER regenerated.
template <typename SecureDirectSend, typename ServerLinkSend>
EgressResult SendExistingGameFrameV240(
    const GameFrame& frame, const PacketEnds& ends,
    const PeerRouteLease& lease, const DirectEgressIdentity& identity,
    SecureDirectSend&& direct_send, ServerLinkSend&& server_send)
{
    const auto relay = [&]() -> EgressResult {
        return server_send(frame) ? EgressResult::Server : EgressResult::Failed;
    };
    if (frame.sender.empty() || !frame.instance || !frame.peer_instance)
        return EgressResult::Failed;  // invalid source identity: fail closed
    const bool eligible = identity.secure_peer_datagram_sender_installed &&
        identity.local_instance == frame.instance &&
        identity.remote_instance == frame.peer_instance &&
        identity.local_instance == lease.granted_sender_instance &&
        identity.remote_instance == lease.granted_receiver_instance &&
        identity.server_authorized_local_id == frame.sender &&
        identity.server_authorized_local_id == lease.granted_sender_id &&
        !identity.server_authorized_remote_id.empty() &&
        identity.server_authorized_remote_id == lease.granted_receiver_id &&
        !identity.server_authorized_party_session_id.empty() &&
        identity.server_authorized_party_session_id == lease.granted_party_session_id &&
        IsExactUnreliableMovement(frame, identity.max_direct_movement_bytes) &&
        ChooseNativePacketCarrier(0x06, ends, lease) == Carrier::DirectPeer;
    if (!eligible) return relay();

    // GameLinkPeer::Flush can piggyback a reliable ACK on an unreliable
    // movement packet. The shadNet link MUST still receive that ACK so
    // its reliable stream does not stall after traffic is offloaded.
    // Direct receiver uses exactly the SAME GameLinkPeer for dedup.
    if (frame.ack != 0) {
        GameFrame ack_only = frame;
        ack_only.entries.clear();
        if (!server_send(ack_only)) return relay(); // retain original on fallback
    }
    GameFrame direct_only = frame;
    direct_only.ack = 0;  // ack went to authoritative server
    if (direct_send(direct_only)) return EgressResult::Direct;
    return relay();  // same seq/instance, so receiver deduplicates either path
}

}  // namespace BloodborneCoop::SHYTHybrid
