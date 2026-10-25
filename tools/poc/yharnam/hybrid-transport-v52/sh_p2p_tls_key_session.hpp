// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V80: one-time per-connection application wrapping key over authenticated
// TLS 1.3 ONLY. The client receives this key inside the TLS cipher channel.
// Still LOCALHOST-ONLY; no peer IPs, no grants and no direct game Arm().
// Do not reuse the key across TLS sessions or after an account/world epoch
// change. Does not depend on Qt 6.12 TLS exporter support.
#include "sh_p2p_tls_identity.hpp"
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
    bool Active() const noexcept{return active_;}
    void Clear() {
        if(!key_.isEmpty())std::fill(key_.begin(),key_.end(),char(0));
        key_.clear();
        if(!account_.isEmpty())std::fill(account_.begin(),account_.end(),char(0));
        account_.clear();
        epoch_=0;active_=false;
    }
private:
    QByteArray key_{};
    QByteArray account_{};
    quint64 epoch_=0;
    bool active_=false;
};
} // namespace SeamlessHunt::Hybrid
