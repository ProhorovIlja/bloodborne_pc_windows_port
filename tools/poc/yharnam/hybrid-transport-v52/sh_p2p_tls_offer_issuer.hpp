// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V81 internal-only server-owned peer offer scope + V75 AEAD offer adapter.
// Public access and client-supplied peer selectors are intentionally absent.
// The ONLY caller is the loopback mTLS test listener. Never ship as a public
// API without secure account onboarding, consent and anti-abuse review.
#include "sh_secure_grant.hpp"
#include <QByteArray>
#include <QCryptographicHash>
#include <QDateTime>
#include <QtEndian>
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace SeamlessHunt::Hybrid {
struct P2PLocalOfferScope {
    QByteArray recipient;               // actual server-authenticated online_id
    QByteArray peer;                    // actual linked online_id, both opted in
    quint64 recipient_epoch=0;          // V77 non-ABA generation
    quint64 peer_epoch=0;
    quint64 world_revision=0;           // same party/map/team/world
    quint32 physical_ipv4_host=0;       // from server's ORIGINAL UDP link
    quint16 physical_port_host=0;
    quint32 virtual_ipv4_host=0;        // from original VirtualEndpointOf
    quint16 virtual_port_host=0;
};
class P2PLocalOfferIssuer final {
public:
    static quint64 AccountToken(const QByteArray& id) {
        if(id.isEmpty())return 0;
        // Domain-separated SHA256, truncated for legacy V75 wire structure.
        // Collision safety also requires rejecting equal tokens for the pair.
        QByteArray input("YT-P2P-V81-ID:");
        input+=id;
        const auto digest=QCryptographicHash::hash(input,QCryptographicHash::Sha256);
        quint64 token=0;
        for(int i=0;i<8;++i)
            token|=quint64(static_cast<quint8>(digest[i]))<<(i*8);
        return token;
    }
    static bool Prepare(const P2PLocalOfferScope& scope,
                        const QByteArray& tls_recipient,
                        quint64 tls_epoch,std::uint64_t now_ms,
                        SecurePeerOffer& offer) {
        offer={};
        if(scope.recipient!=tls_recipient ||
           !tls_epoch || scope.recipient_epoch!=tls_epoch ||
           scope.recipient.isEmpty() || scope.peer.isEmpty() ||
           scope.recipient==scope.peer || !scope.peer_epoch ||
           !scope.world_revision || !scope.physical_ipv4_host ||
           !scope.physical_port_host || !scope.virtual_ipv4_host ||
           !scope.virtual_port_host || !now_ms ||
           now_ms>UINT64_MAX-10000)return false;
        const quint64 recip=AccountToken(scope.recipient);
        const quint64 peer=AccountToken(scope.peer);
        if(!recip || !peer || recip==peer)return false;
        std::array<std::uint8_t,40> random{};
        if(!SecureOfferDetail::Random(random))return false;
        quint64 pair=0;
        for(unsigned i=0;i<8;++i)
            pair|=quint64(random[i]) << (i*8);
        if(!pair){CryptoDetail::Erase(random);return false;}
        offer.sender_account=peer;
        offer.recipient_account=recip;
        offer.session_epoch=tls_epoch;
        offer.pair_binding=pair;
        offer.world_revision=scope.world_revision;
        offer.issued_ms=now_ms;
        offer.expires_ms=now_ms+10000; // 10s one-time local test lease
        offer.peer_ipv4_nbo=qToBigEndian(scope.physical_ipv4_host);
        offer.peer_port_nbo=qToBigEndian(scope.physical_port_host);
        offer.peer_virtual_ipv4_nbo=qToBigEndian(scope.virtual_ipv4_host);
        offer.peer_virtual_port_nbo=qToBigEndian(scope.virtual_port_host);
        std::copy(random.begin()+8,random.end(),offer.direction_key.begin());
        CryptoDetail::Erase(random);
        if(!SecureOfferDetail::Valid(offer,now_ms)) {
            CryptoDetail::Erase(offer.direction_key);offer={};
            return false;
        }
        return true;
    }
};
} // namespace SeamlessHunt::Hybrid
