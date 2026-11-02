// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V310: actual server-only EdDSA peer-grant issuer for original YT CoopStream.
// Uses server-observed shadNet UDP links from V308, the responder's own
// authenticated consent, and a FRESH OS-backed 128-bit grant nonce.
// This function does NOT install a signer or derive an EdDSA secret from
// any client, nor does it establish NAT reachability or a Noise session.
#include "yt_signed_peer_grant_v279.h"
#include "coop.pb.h"
#include <QDateTime>
#include <QRandomGenerator>
#include <QtEndian>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <limits>
#include <optional>
#include <string>
#include <string_view>

namespace BloodborneCoop::SHYTHybrid::ServerDirectSignerV310 {
namespace Grant=SignedPeerGrantV279;

// Source must be Service::DirectPairSource from the real authenticated
// Service::Take route; there is intentionally NO client-side source form.
template<class Source>
std::optional<bbcoop::Envelope> Issue(
    const Source& src,
    const bbcoop::DirectPeerRequest& sender_intent,
    const Grant::SecretKey& operator_secret,
    const Grant::PubKey& operator_public)
{
    if (!Grant::NonZero(operator_public) ||
        !Grant::NonZero(operator_secret) ||
        src.sender.empty() || src.receiver.empty() ||
        src.sender==src.receiver || src.sender_run==0 ||
        src.receiver_run==0 ||
        src.sender_game_link_instance==0 ||
        sender_intent.game_link_instance()!=src.sender_game_link_instance ||
        sender_intent.recipient()!=src.receiver ||
        sender_intent.noise_static_public_key().size()!=32 ||
        sender_intent.request_nonce().size()!=16 ||
        src.responder_noise_static_key.size()!=32 ||
        src.sender_link.Key()==src.receiver_link.Key() ||
        !src.sender_link.ipv4 || !src.sender_link.port ||
        !src.receiver_link.ipv4 || !src.receiver_link.port)
        return std::nullopt;

    const auto responder=reinterpret_cast<const u8*>(
        src.responder_noise_static_key.data());
    const auto initiator=reinterpret_cast<const u8*>(
        sender_intent.noise_static_public_key().data());
    const auto client_nonce=reinterpret_cast<const u8*>(
        sender_intent.request_nonce().data());
    if (!Grant::NonZero(std::span<const u8>(responder,32)) ||
        !Grant::NonZero(std::span<const u8>(initiator,32)) ||
        !Grant::NonZero(std::span<const u8>(client_nonce,16)) ||
        std::equal(responder,responder+32,initiator))
        return std::nullopt;

    Grant::Scope scope{};
    scope.team=src.team;
    scope.party=src.party;
    scope.sender=src.sender;
    scope.receiver=src.receiver;
    scope.sender_instance=src.sender_game_link_instance;
    scope.receiver_instance=src.receiver_game_link_instance;
    scope.map=src.map;
    scope.world_epoch=src.world_epoch;
    scope.sender_ip_nbo=qToBigEndian(src.sender_link.ipv4);
    scope.receiver_ip_nbo=qToBigEndian(src.receiver_link.ipv4);
    scope.sender_port_nbo=qToBigEndian(src.sender_link.port);
    scope.receiver_port_nbo=qToBigEndian(src.receiver_link.port);
    std::copy_n(responder,32,scope.responder_noise_pub.begin());

    scope.issued_unix_ms=QDateTime::currentMSecsSinceEpoch();
    constexpr s64 TicketMs=20'000;
    if (scope.issued_unix_ms<=0 ||
        scope.issued_unix_ms>std::numeric_limits<s64>::max()-TicketMs)
        return std::nullopt;
    scope.expires_unix_ms=scope.issued_unix_ms+TicketMs;

    // QRandomGenerator::system is Qt's OS entropy-backed generator.
    // Use an aligned word buffer instead of misaligning byte-array data.
    std::array<quint32,4> entropy{};
    QRandomGenerator::system()->fillRange(entropy.data(),entropy.size());
    std::memcpy(scope.grant_nonce.data(),entropy.data(),scope.grant_nonce.size());
    if (!Grant::NonZero(scope.grant_nonce))
        return std::nullopt;
    const auto signed_ticket=Grant::Sign(scope,operator_secret);
    const Grant::Expect view{
        src.team,src.party,src.sender,src.receiver,
        src.sender_game_link_instance,src.receiver_game_link_instance,
        src.map,src.world_epoch};
    if (!signed_ticket ||
        !Grant::Verify(*signed_ticket,operator_public,view,
                       scope.issued_unix_ms))
        return std::nullopt;
    const auto bytes=Grant::EncodeWire(*signed_ticket);
    if (bytes.empty() || bytes.size()>512)
        return std::nullopt;
    bbcoop::Envelope response{};
    auto* ticket=response.mutable_direct_peer_grant();
    ticket->set_authority_public_key(std::string(
        reinterpret_cast<const char*>(operator_public.data()),
        operator_public.size()));
    ticket->set_signed_grant(std::string(
        reinterpret_cast<const char*>(bytes.data()),bytes.size()));
    return response;
}

} // namespace BloodborneCoop::SHYTHybrid::ServerDirectSignerV310
