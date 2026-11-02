// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// SHYT v1.3.1 experimental hybrid ingress gate, source-tested with real
// lKaniel bloodborne-server GameFrame and GameLinkPeer protocol types.
//
// This gate does NOT authenticate UDP. Cryptographic packet authentication,
// fresh endpoint validation and server-authoritative lease granting MUST
// happen BEFORE this function. Until then direct traffic remains disabled.
//
// GameLinkPeer maintains the EXACT SAME stream/instance for both carriers,
// with its own unreliable per-channel sequence deduplication. Never create
// one GameLinkPeer per carrier: that would allow stale relay packets to
// re-execute already processed native movement or reset reliable streams.
#include <cstddef>
#include <string_view>
#include "hybrid_transport_policy_v1.h"

namespace BloodborneCoop::SHYTHybrid {

struct DirectIngressIdentity {
    // These IDs/instances must come from the authenticated game-server
    // session, NOT a peer-supplied untrusted datagram.
    std::string_view server_authorized_remote_id;
    u32 server_authorized_remote_instance = 0;
    u32 local_instance = 0;
    size_t max_native_movement_bytes = 1100;
    std::string_view server_authorized_local_id;
    std::string_view server_authorized_party_session_id;
};

// Route and identity validation is deliberately separate from the original
// GameLinkPeer::Receive; never call Receive on an unvalidated direct frame.
// This protects against late pre-restart frames changing peer_instance and
// resetting the original GameLinkPeer reliable/unreliable streams.
//
// Note: caller must check cryptographic datagram MAC and endpoint before
// decoding GameFrame. A name, boolean or uint32 instance alone is NOT
// authentication or NAT traversal.
inline bool AcceptAuthenticatedDirectMovement(
    const GameFrame& frame, const PacketEnds& ends,
    const PeerRouteLease& lease, const DirectIngressIdentity& identity)
{
    if (ChooseNativePacketCarrier(0x06, ends, lease) != Carrier::DirectPeer)
        return false;
    // Explicitly bind the server-granted transport lease to BOTH parties.
    // The UDP sender and the receiver session must not borrow another
    // peer-pair lease after a join, host handoff or connection restart.
    if (identity.server_authorized_remote_id.empty() ||
        identity.server_authorized_local_id.empty() ||
        lease.granted_sender_id != identity.server_authorized_remote_id ||
        lease.granted_receiver_id != identity.server_authorized_local_id ||
        identity.server_authorized_party_session_id.empty() ||
        identity.server_authorized_party_session_id !=
            lease.granted_party_session_id ||
        identity.server_authorized_remote_instance !=
            lease.granted_sender_instance ||
        identity.local_instance != lease.granted_receiver_instance ||
        !identity.server_authorized_remote_instance || !identity.local_instance ||
        frame.sender != identity.server_authorized_remote_id ||
        frame.instance != identity.server_authorized_remote_instance ||
        frame.peer_instance != identity.local_instance ||
        // A direct movement-only frame must NOT carry an ACK for a
        // server-managed reliable stream. Otherwise a valid direct
        // datagram could spuriously acknowledge reliable world data.
        frame.ack != 0 ||
        frame.entries.empty() || frame.entries.size() > 8)
        return false;
    for (const GameFrameEntry& entry : frame.entries) {
        if (entry.packet_class != PacketClass::Unreliable ||
            entry.packet.size() < 8 ||
            entry.packet.size() > identity.max_native_movement_bytes)
            return false;
        const auto& b = entry.packet;
        const auto little32 = [&b](size_t off) -> u32 {
            return u32{b[off]} | (u32{b[off+1]} << 8) |
                   (u32{b[off+2]} << 16) | (u32{b[off+3]} << 24);
        };
        if (little32(0) != 0x06 || little32(4) != b.size()-8)
            return false;
    }
    return true;
}

} // namespace BloodborneCoop::SHYTHybrid
