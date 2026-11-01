// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V262: inbound half of the ACTUAL YT source integration seam.
// The call site holds a reference to the EXISTING GameLinkPeer from
// game_link.peers. NEVER create a new receiver for P2P or trust a name in
// a peer-supplied UDP packet. Standalone OS UDP socket/ICE integration
// and server-attested endpoint binding are still required.
#include "hybrid_peer_crypto_v241.h"
#include <cstdint>
#include <span>
#include <utility>
#include <vector>

namespace BloodborneCoop::SHYTHybrid {

struct VerifiedPeerIngressV262 {
    PeerCryptoDatagramsV241* session = nullptr;
    PeerRouteLease lease{};
    DirectIngressIdentity identity{};
    PacketEnds endpoints{};
    // A server-granted / direct-handshake-proved IP:port for this exact
    // party pair; neither may come from the incoming datagram itself.
    std::pair<u32,u16> approved_endpoint{};
    bool endpoint_proved_by_authenticated_handshake = false;
};

// The only side effect on success is ORIGINAL GameLinkPeer::Receive.
// On every denial GameLinkPeer state is untouched. A successful AEAD
// packet with wrong channel/lease can consume its replay counter,
// which is harmless and avoids accepting it again after an epoch shift.
inline std::vector<std::vector<u8>> ReceiveDirectYtFrameV262(
    GameLinkPeer& original_receiver,
    VerifiedPeerIngressV262& authorized,
    std::pair<u32,u16> udp_source,
    std::span<const u8> received_wire)
{
    if (!authorized.session ||
        !authorized.endpoint_proved_by_authenticated_handshake ||
        !authorized.approved_endpoint.first ||
        !authorized.approved_endpoint.second ||
        udp_source != authorized.approved_endpoint ||
        !authorized.session->MatchesIncomingGrantV262(
            authorized.lease, authorized.identity, authorized.endpoints) ||
        ChooseNativePacketCarrier(0x06,authorized.endpoints,
                                  authorized.lease) != Carrier::DirectPeer)
        return {};
    // OpenMovement first verifies ChaCha20-Poly1305 + original YT
    // replay window and per-sender GameFrame identities.
    auto decoded=authorized.session->OpenMovement(received_wire);
    if (!decoded || !AcceptAuthenticatedDirectMovement(
            *decoded,authorized.endpoints,authorized.lease,
            authorized.identity))
        return {};
    return original_receiver.Receive(*decoded,authorized.lease.now_ms);
}
} // namespace BloodborneCoop::SHYTHybrid
