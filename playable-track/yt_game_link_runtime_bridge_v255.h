// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V255: ABI-light source integration seam for ORIGINAL YT 1.3.1
// bloodborne_patches.cpp RunGamePacketLink. Keep Flush under the game's
// mutex, but call Dispatch outside that mutex. No extra GameLinkPeer.
// Default route is 100% identical server SHAD/GamePacketsType envelope.
// In production the direct state MUST be instantiated only after a
// server-authenticated peer pair grant + OS CSPRNG Noise handshake,
// endpoint validation and lifecycle revocation. No bool is an auth proof.
#include "hybrid_peer_crypto_v241.h"
#include "yt_shdp_wire_v286.h"
#include "hybrid_direct_ack_coalescer_v251.h"
#include <cstdint>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace BloodborneCoop::SHYTHybrid {

struct PendingYtFrameV255 {
    std::string member;
    std::pair<u32,u16> existing_server_link_address;
    GameFrame frame;
};

struct VerifiedPeerRouteV255 {
    // All views and crypto objects are owned by the game session, never
    // pointers into temporary RPC packets; one route per ordered pair.
    PeerRouteLease lease{};
    DirectEgressIdentity identity{};
    PacketEnds endpoints{};
    PeerCryptoDatagramsV241* peer_crypto=nullptr;
    DirectAckCoalescerV251* ack_tracker=nullptr;
    // V258: never offload movement if the receiving client has not
    // attached its authenticated peer UDP ingest to the SAME GameLinkPeer.
    // Otherwise the send succeeds but remote movement is silently lost.
    bool same_peer_ingress_installed = false;
};

// Callbacks return true ONLY when the underlying transport accepted the
// complete datagram. A false direct result triggers the unmodified relay.
// The original shadNet server link handles reliable/world packets.
template<class ExistingServerSend, class AuthenticatedPeerWireSend>
EgressResult DispatchYtFrameV255(
    const PendingYtFrameV255& pending,
    VerifiedPeerRouteV255* active_grant,
    ExistingServerSend&& original_server_send,
    AuthenticatedPeerWireSend&& peer_wire_send)
{
    const auto relay = [&](const GameFrame& frame) -> bool {
        std::vector<u8> datagram{'S','H','A','D',GamePacketsType};
        const auto encoded=EncodeGameFrame(frame);
        datagram.insert(datagram.end(),encoded.begin(),encoded.end());
        return original_server_send(pending.existing_server_link_address,
                                    std::span<const u8>(datagram));
    };
    // Fail closed to the real server without speculative key generation,
    // guessed remote endpoint, copied session or separate sequence number.
    if(!active_grant || !active_grant->peer_crypto ||
       !active_grant->ack_tracker ||
       !active_grant->same_peer_ingress_installed ||
       pending.member != active_grant->identity.server_authorized_remote_id ||
       !active_grant->peer_crypto->MatchesOutgoingGrantV258(
           active_grant->lease,active_grant->identity,active_grant->endpoints))
        return relay(pending.frame) ? EgressResult::Server : EgressResult::Failed;

    const auto secure_direct = [&](const GameFrame& movement) -> bool {
        const auto encrypted=active_grant->peer_crypto->SealMovement(movement);
        if (!encrypted) return false;
        // V286: OS physical socket accepts SHDP-v1 framed ciphertext,
        // while V241 seals only the original GameFrame AEAD payload.
        // Enforce MTU inclusive of the 9-byte channel header.
        const auto physical=ShdpWireV286::Wrap(*encrypted);
        if (!physical) return false; // server route fallback
        return peer_wire_send(pending.member,std::span<const u8>(*physical));
    };
    return SendExistingGameFrameV251(
        pending.frame, active_grant->endpoints,
        active_grant->lease, active_grant->identity,
        *active_grant->ack_tracker, secure_direct, relay);
}
} // namespace BloodborneCoop::SHYTHybrid
