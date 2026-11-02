// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V289: real compiled original YT bbcoop::Envelope -> signed grant
// adapter. Must be called ONLY inside the already authenticated/reliable
// original shadNet server CoopStream, never on raw peer UDP or guest SHAD.
// Server must build scope from authoritative TeamLobby/world/LinkAuth
// data; the client must independently pin authority_pub through a
// separately trusted configuration or original pinned server link.
#include "yt_server_team_grant_issuer_v283.h"
#include "coop.pb.h"
#include <algorithm>
#include <optional>
#include <span>
#include <string>

namespace BloodborneCoop::SHYTHybrid::SignedGrantCoopV289 {
namespace Grant=SignedPeerGrantV279;

template<class Team>
std::optional<bbcoop::Envelope> ServerIssue(
    const Team& authoritative_team,
    const Grant::Scope& server_derived_scope,
    std::string_view original_authenticated_link_member,
    std::size_t authoritative_server_team_limit,
    const Grant::SecretKey& server_only_secret,
    const Grant::PubKey& authority_public_key)
{
    if(!Grant::NonZero(authority_public_key))
        return std::nullopt;
    const auto signed_grant=ServerTeamIssuerV283::Issue(
        authoritative_team,server_derived_scope,
        original_authenticated_link_member,
        authoritative_server_team_limit,server_only_secret);
    if(!signed_grant)return std::nullopt;
    // V291: catch a broken server key configuration BEFORE publishing:
    // the authority public key advertised over the existing Coop link
    // must actually verify a signature made by the configured private
    // signing key. A mismatched key pair never opens peer routing.
    const Grant::Expect scope_view{
        server_derived_scope.team,server_derived_scope.party,
        server_derived_scope.sender,server_derived_scope.receiver,
        server_derived_scope.sender_instance,
        server_derived_scope.receiver_instance,
        server_derived_scope.map,server_derived_scope.world_epoch};
    if(!Grant::Verify(*signed_grant,authority_public_key,scope_view,
                      server_derived_scope.issued_unix_ms))
        return std::nullopt;
    const auto bytes=Grant::EncodeWire(*signed_grant);
    if(bytes.empty() || bytes.size()>512)return std::nullopt;
    bbcoop::Envelope message{};
    auto* body=message.mutable_direct_peer_grant();
    body->set_signed_grant(
        std::string(reinterpret_cast<const char*>(bytes.data()),bytes.size()));
    body->set_authority_public_key(
        std::string(reinterpret_cast<const char*>(authority_public_key.data()),
                    authority_public_key.size()));
    return message;
}

// Receiving the protobuf is NOT an authorization event. It only
// produces a verified grant after checking the pinned authority, exact
// original Noise session scope, current world state and EdDSA signature.
// Live session/endpoint V285 checks and physical V262 AEAD still apply.
inline std::optional<Grant::Signed> ClientTake(
    const bbcoop::Envelope& original_authenticated_server_coop_message,
    const Grant::PubKey& independently_trusted_authority,
    const Grant::Expect& live_authoritative_view,
    const PeerCryptoScopeV241& live_noise_scope,
    const Grant::PubKey& pinned_responder_noise_pub,
    s64 now_unix_ms)
{
    if(!original_authenticated_server_coop_message.has_direct_peer_grant() ||
       !Grant::NonZero(independently_trusted_authority))
        return std::nullopt;
    const auto& body=original_authenticated_server_coop_message.direct_peer_grant();
    if(body.signed_grant().empty() || body.signed_grant().size()>512 ||
       body.authority_public_key().size()!=
           independently_trusted_authority.size())
        return std::nullopt;
    // This authenticated Coop field is an identity assertion, not a
    // replacement for the local authority pin.
    const auto* pub=reinterpret_cast<const u8*>(
        body.authority_public_key().data());
    if(!std::equal(independently_trusted_authority.begin(),
                   independently_trusted_authority.end(),pub))
        return std::nullopt;
    const auto* wire=reinterpret_cast<const u8*>(body.signed_grant().data());
    auto decoded=Grant::DecodeWire(
        std::span<const u8>(wire,body.signed_grant().size()));
    if(!decoded || !Grant::AuthorizesNoiseScope(
        *decoded,independently_trusted_authority,live_authoritative_view,
        now_unix_ms,live_noise_scope,pinned_responder_noise_pub))
        return std::nullopt;
    return decoded;
}
} // namespace BloodborneCoop::SHYTHybrid::SignedGrantCoopV289
