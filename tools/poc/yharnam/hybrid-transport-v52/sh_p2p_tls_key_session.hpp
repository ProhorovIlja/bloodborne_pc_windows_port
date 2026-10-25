// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V80: one-time per-connection application wrapping key over authenticated
// TLS 1.3 ONLY. The client receives this key inside the TLS cipher channel.
// Still LOCALHOST-ONLY; no peer IPs, no grants and no direct game Arm().
// Do not reuse the key across TLS sessions or after an account/world epoch
// change. Does not depend on Qt 6.12 TLS exporter support.
#include "sh_p2p_tls_identity.hpp"
#include "sh_p2p_tls_offer_issuer.hpp"
#include "sh_p2p_tls_offer_v84.hpp" // V85 full-width SHG2, local mTLS test only
#include <QByteArray>
#include <QRandomGenerator>
#include <QSslCertificate>
#include <algorithm>
#include <utility>

namespace SeamlessHunt::Hybrid {
class P2PTlsKeySession final {
public:
    P2PTlsKeySession()=default;
    ~P2PTlsKeySession(){Clear();}
    P2PTlsKeySession(const P2PTlsKeySession&)=delete;
    P2PTlsKeySession& operator=(const P2PTlsKeySession&)=delete;
    bool Begin(const BoundP2PAccount& bound, QByteArray& reply) {
        reply.clear();
        if(active_ || bound.account.isEmpty() || !bound.current_epoch)
            return false;  // no renegotiation/replay within a TLS connection
        QByteArray fresh(32, '\0');
        // Qt's system random generator is OS-backed; no repeatable PRNG
        // or account/password-derived material may seed a session key.
        for(int i=0;i<8;++i) {
            const quint32 v=QRandomGenerator::system()->generate();
            for(int j=0;j<4;++j)
                fresh[i*4+j]=char((v>>(8*j))&0xff);
        }
        if(std::all_of(fresh.cbegin(),fresh.cend(),
                       [](char c){return c==0;})) {
            std::fill(fresh.begin(),fresh.end(),char(0));
            return false;
        }
        account_=bound.account;
        epoch_=bound.current_epoch;
        key_=std::move(fresh);
        active_=true;
        // This response must ONLY be written to an already peer-verified
        // TLS 1.3 QSslSocket. No logger/HTTP/SHLK may print/copy it.
        reply="YT-P2P/V80 KEY "+key_.toHex()+"\n";
        return true;
    }
    bool StillBound(const P2PTlsIdentity& identity,
                    const QSslCertificate& certificate) const {
        if(!active_ || key_.size()!=32 || !epoch_) return false;
        const auto current=identity.Resolve(certificate);
        return current && current->account==account_ &&
               current->current_epoch==epoch_;
    }
    // V81: after this SAME mTLS socket's V80 BEGIN, issue at most ONE
    // internally derived, recipient-specific V75 AES-GCM offer. The peer
    // selector and all endpoints originate from shadNet's authoritative
    // current links/world, NEVER from arbitrary client request contents.
    bool SealOneLocalOffer(const P2PTlsIdentity& identity,
                           const QSslCertificate& cert,
                           const P2PLocalOfferScope& scope,
                           QByteArray& tls_response) {
        tls_response.clear();
        if(offer_sent_ || !StillBound(identity,cert))return false;
        SecurePeerOffer offer{};
        const auto now=static_cast<std::uint64_t>(
            QDateTime::currentMSecsSinceEpoch());
        if(!P2PLocalOfferIssuer::Prepare(scope,account_,epoch_,now,offer))
            return false;
        SealedPeerOffers sealer;
        const auto raw_key=std::span<const std::uint8_t>(
            reinterpret_cast<const std::uint8_t*>(key_.constData()),
            static_cast<std::size_t>(key_.size()));
        if(!sealer.InstallChannelKey(raw_key)) {
            CryptoDetail::Erase(offer.direction_key);
            return false;
        }
        std::vector<std::uint8_t> wire;
        const bool sealed=sealer.Seal(offer,now,wire);
        CryptoDetail::Erase(offer.direction_key);
        if(!sealed)return false;
        tls_response="YT-P2P/V81 OFFER "+QByteArray(
            reinterpret_cast<const char*>(wire.data()),
            static_cast<qsizetype>(wire.size())).toHex()+"\n";
        CryptoDetail::Erase(wire);
        offer_sent_=true;
        return true;
    }
    // V85: mutually exclusive with legacy V81. Exactly one SHG2 record
    // on this SAME authenticated TLS 1.3 connection after V80 BEGIN.
    // Untrusted client never supplies account, peer selector or endpoints.
    bool SealOneLocalOfferV84(const P2PTlsIdentity& identity,
                              const QSslCertificate& cert,
                              const P2PLocalOfferScope& scope,
                              QByteArray& tls_response) {
        tls_response.clear();
        if(offer_sent_ || !StillBound(identity,cert))return false;
        SecurePeerOfferV84 offer{};
        const auto now=static_cast<std::uint64_t>(
            QDateTime::currentMSecsSinceEpoch());
        if(!P2PFullIdentityIssuerV84::Prepare(scope,account_,epoch_,now,offer))
            return false;
        SealedPeerOffersV84 sealer;
        const auto raw_key=std::span<const std::uint8_t>(
            reinterpret_cast<const std::uint8_t*>(key_.constData()),
            static_cast<std::size_t>(key_.size()));
        if(!sealer.InstallChannelKey(raw_key)) {
            CryptoDetail::Erase(offer.direction_key);
            return false;
        }
        std::vector<std::uint8_t> wire;
        const bool sealed=sealer.Seal(offer,now,wire);
        CryptoDetail::Erase(offer.direction_key);
        if(!sealed || wire.size()!=SecureOfferV84Detail::kWireBytes)return false;
        tls_response="YT-P2P/V84 OFFER "+QByteArray(
            reinterpret_cast<const char*>(wire.data()),
            static_cast<qsizetype>(wire.size())).toHex()+"\n";
        CryptoDetail::Erase(wire);
        offer_sent_=true;
        return true;
    }
    bool Active() const noexcept{return active_;}
    void Clear() {
        if(!key_.isEmpty())std::fill(key_.begin(),key_.end(),char(0));
        key_.clear();
        if(!account_.isEmpty())std::fill(account_.begin(),account_.end(),char(0));
        account_.clear();
        epoch_=0;active_=false;offer_sent_=false;
    }
private:
    QByteArray key_{};
    QByteArray account_{};
    quint64 epoch_=0;
    bool active_=false;
    bool offer_sent_=false;
};
} // namespace SeamlessHunt::Hybrid
