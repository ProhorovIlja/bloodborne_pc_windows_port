// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V285: cryptographic admission barrier between shadNet's real signed
// pair grant and the original YT physical peer socket. A caller cannot
// install an endpoint with merely V262's booleans or an arbitrary UDP IP.
//
// The 32-byte authority MUST be pre-pinned from the authenticated
// server link / trusted launcher configuration, NEVER copied from the
// incoming peer packet. This module verifies a caller-provided pin; it
// does not yet implement server-side provisioning of that trusted pin.
#include "yt_game_link_direct_ingress_v262.h"
#include "yt_signed_peer_grant_v279.h"

namespace BloodborneCoop::SHYTHybrid {
struct SignedPeerIngressV285 {
    VerifiedPeerIngressV262 receiver{};
    SignedPeerGrantV279::Signed issued_by_server{};
    SignedPeerGrantV279::PubKey pinned_authority_pub{};
    SignedPeerGrantV279::Expect live_server_view{};
    PeerCryptoScopeV241 noise_scope{};
    SignedPeerGrantV279::PubKey responder_noise_pub{};
    s64 now_unix_ms=0;
};

// Expected role is **incoming**: signed sender is the authenticated
// remote hunter, receiver is the local hunter. A grant's sender IP:port
// must match the same peer address that the original YT UDP socket will
// allow. All session/epoch and channel checks remain in V262.
inline bool ValidateSignedPeerIngressV285(const SignedPeerIngressV285& proof) {
    namespace Grant=SignedPeerGrantV279;
    const auto& g=proof.issued_by_server.scope;
    const auto& entry=proof.receiver;
    return entry.session && entry.endpoint_proved_by_authenticated_handshake &&
        Grant::AuthorizesNoiseScope(proof.issued_by_server,
                                   proof.pinned_authority_pub,
                                   proof.live_server_view,proof.now_unix_ms,
                                   proof.noise_scope,proof.responder_noise_pub) &&
        g.sender==entry.identity.server_authorized_remote_id &&
        g.receiver==entry.identity.server_authorized_local_id &&
        g.party==entry.identity.server_authorized_party_session_id &&
        g.sender_instance==entry.identity.server_authorized_remote_instance &&
        g.receiver_instance==entry.identity.local_instance &&
        g.sender_ip_nbo==entry.approved_endpoint.first &&
        g.sender_port_nbo==entry.approved_endpoint.second &&
        entry.lease.granted_party_session_id==g.party &&
        entry.lease.granted_sender_id==g.sender &&
        entry.lease.granted_receiver_id==g.receiver &&
        entry.lease.granted_sender_instance==g.sender_instance &&
        entry.lease.granted_receiver_instance==g.receiver_instance &&
        entry.lease.local_world_epoch==g.world_epoch &&
        entry.lease.authority_epoch==g.world_epoch &&
        entry.lease.approved_sender_map==g.map &&
        entry.lease.approved_target_map==g.map &&
        entry.session->MatchesIncomingGrantV262(
            entry.lease,entry.identity,entry.endpoints) &&
        ChooseNativePacketCarrier(0x06,entry.endpoints,entry.lease)
            ==Carrier::DirectPeer;
}
} // namespace BloodborneCoop::SHYTHybrid
