// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V79: local-only operator-pinned certificate -> game account binding.
// A TLS client certificate common name or client-provided account claim
// NEVER identifies an account. Only exact SHA-256 DER pin set by a local
// privileged operator, plus current server-authoritative live game session
// can authorize BIND. No direct grants are issued by this component.
#include <QByteArray>
#include <QCryptographicHash>
#include <QHash>
#include <QRegularExpression>
#include <QSslCertificate>
#include <QString>
#include <functional>
#include <optional>

namespace SeamlessHunt::Hybrid {
struct BoundP2PAccount {
    QByteArray account;
    quint64 current_epoch=0;
};
class P2PTlsIdentity final {
public:
    using LiveEpoch=std::function<quint64(const QByteArray&)>;
    // Operator provisioning ONLY. Never expose as an unauthenticated route.
    bool AddLocalPin(const QByteArray& certificate_sha256_hex,
                     const QByteArray& server_online_id) {
        if (certificate_sha256_hex.size()!=64 ||
            server_online_id.isEmpty() || server_online_id.size()>64 ||
            server_online_id.contains('\n') ||
            server_online_id.contains('\r') ||
            server_online_id.contains('\0'))return false;
        const auto pin=QByteArray::fromHex(certificate_sha256_hex);
        if(pin.size()!=32 || pin.toHex()!=certificate_sha256_hex.toLower() ||
           std::all_of(pin.cbegin(),pin.cend(),[](char c){return c==0;}))
            return false;
        if(pins_.contains(pin))return false; // no override of existing identity
        for(auto it=pins_.cbegin();it!=pins_.cend();++it)
            if(it.value()==server_online_id)return false; // one identity => one cert
        pins_.insert(pin,server_online_id);return true;
    }
    void SetLiveEpochResolver(LiveEpoch resolver) {
        live_epoch_=std::move(resolver);
    }
    std::optional<BoundP2PAccount> Resolve(const QSslCertificate& peer) const {
        if(peer.isNull() || !live_epoch_)return std::nullopt;
        const auto fingerprint=QCryptographicHash::hash(
            peer.toDer(),QCryptographicHash::Sha256);
        const auto found=pins_.constFind(fingerprint);
        if(found==pins_.cend())return std::nullopt;
        const auto epoch=live_epoch_(found.value());
        if(!epoch)return std::nullopt;
        return BoundP2PAccount{found.value(),epoch};
    }
    void Clear() {
        pins_.clear();live_epoch_={};
    }
private:
    QHash<QByteArray,QByteArray> pins_{};
    LiveEpoch live_epoch_{};
};
} // namespace SeamlessHunt::Hybrid
