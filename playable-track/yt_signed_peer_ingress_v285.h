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
#include <algorithm>
#include <limits>
#include <optional>

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

// V304: the OS socket uses steady-clock milliseconds but the server
// signs wall-clock Unix milliseconds. Verify the grant against FRESH
// local wall time at installation, then cap the physical route to BOTH
// the existing original GameLink lease and the signed ticket's expiry.
// A 30-second signed ticket must never leave a 10-minute socket gate.
inline std::optional<s64> BoundedPhysicalPeerExpiryV304(
    const SignedPeerIngressV285& proof,
    s64 observed_steady_ms, s64 observed_unix_ms)
{
    namespace Grant=SignedPeerGrantV279;
    if (!ValidateSignedPeerIngressV285(proof) ||
        observed_steady_ms<0 || observed_unix_ms<=0 ||
        observed_steady_ms>std::numeric_limits<s64>::max()-35'000 ||
        !Grant::Verify(proof.issued_by_server,proof.pinned_authority_pub,
                       proof.live_server_view,observed_unix_ms))
        return std::nullopt;
    const s64 remaining=
        proof.issued_by_server.scope.expires_unix_ms-observed_unix_ms;
    if (remaining<=0 || remaining>35'000)
        return std::nullopt;
    const s64 capped=std::min(
        proof.receiver.lease.lease_expiry_ms,
        observed_steady_ms+remaining);
    if (capped<=observed_steady_ms)
        return std::nullopt;
    return capped;
}
} // namespace BloodborneCoop::SHYTHybrid
