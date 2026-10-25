// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V84 Qt-side source-only full-width account identity adapter for SHG2.
// Only call AFTER original shadNet verified TLS client, both online game
// sessions, current world/map/team/consent and physical+virtual peer route.
// This does NOT open public TLS, send grants, or activate Direct game UDP.
#include "sh_p2p_tls_offer_issuer.hpp"
#include "sh_secure_grant_v84.hpp"
#include <QByteArray>
#include <QCryptographicHash>
#include <QtEndian>
#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>

namespace SeamlessHunt::Hybrid {
class P2PFullIdentityIssuerV84 final {
public:
    static std::optional<std::array<std::uint8_t,32>> AccountDigest(
        const QByteArray& online_id) {
        if(online_id.isEmpty() || online_id.size()>64 ||
           online_id.contains('\n') || online_id.contains('\r') ||
           online_id.contains('\0'))return std::nullopt;
        QByteArray input("YT-P2P-V84-ID:");
        input+=online_id;
        const auto digest=QCryptographicHash::hash(
            input,QCryptographicHash::Sha256);
        if(digest.size()!=32)return std::nullopt;
        std::array<std::uint8_t,32> out{};
        std::copy_n(reinterpret_cast<const std::uint8_t*>(
            digest.constData()),out.size(),out.begin());
        return out;
    }
    static bool Prepare(const P2PLocalOfferScope& scope,
                        const QByteArray& authenticated_tls_recipient,
                        quint64 current_tls_epoch,std::uint64_t now_ms,
                        SecurePeerOfferV84& out) {
        out={};
        if(scope.recipient!=authenticated_tls_recipient ||
           !current_tls_epoch || scope.recipient_epoch!=current_tls_epoch ||
           scope.recipient==scope.peer || !scope.peer_epoch ||
           !scope.world_revision || !scope.physical_ipv4_host ||
           !scope.physical_port_host || !scope.virtual_ipv4_host ||
           !scope.virtual_port_host || !now_ms ||
           now_ms>UINT64_MAX-10000)return false;
        const auto recipient=AccountDigest(scope.recipient);
        const auto sender=AccountDigest(scope.peer);
        if(!recipient || !sender ||
           SecureOfferV84Detail::EqualDigest(*recipient,*sender) ||
           !SecureOfferV84Detail::Nonzero(*recipient) ||
           !SecureOfferV84Detail::Nonzero(*sender))return false;
        std::array<std::uint8_t,40> random{};
        if(!SecureOfferV84Detail::Random(random))return false;
        std::uint64_t pair=0;
        for(unsigned i=0;i<8;++i)
            pair|=std::uint64_t(random[i])<<(i*8);
        if(!pair) {
            CryptoDetail::Erase(random);
            return false;
        }
        out.sender_account=*sender;
        out.recipient_account=*recipient;
        out.session_epoch=current_tls_epoch;
        out.pair_binding=pair;
        out.world_revision=scope.world_revision;
        out.issued_ms=now_ms;
        out.expires_ms=now_ms+10000;
        out.peer_ipv4_nbo=qToBigEndian(scope.physical_ipv4_host);
        out.peer_port_nbo=qToBigEndian(scope.physical_port_host);
        out.peer_virtual_ipv4_nbo=qToBigEndian(scope.virtual_ipv4_host);
        out.peer_virtual_port_nbo=qToBigEndian(scope.virtual_port_host);
        std::copy(random.begin()+8,random.end(),out.direction_key.begin());
        CryptoDetail::Erase(random);
        if(!SecureOfferV84Detail::Valid(out,now_ms)) {
            CryptoDetail::Erase(out.direction_key);
            out={};
            return false;
        }
        return true;
    }
};
} // namespace SeamlessHunt::Hybrid
