// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V78: real Qt TLS 1.3 listener, in the SAME shadNet process.
// Development loopback-only, disabled by default, mutual X.509 certificate
// verification mandatory. NO grant issuance/account mapping or peer disclosure.
// In particular never forward client-submitted identities, TLS 1.2 fallback,
// plaintext SHLK/HTTP, or an unverified certificate to the V75 grant codec.
#include <QByteArray>
#include <QFile>
#include <QHostAddress>
#include <QSet>
#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslKey>
#include <QSslSocket>
#include <QTcpServer>
#include <QTimer>
#include <QThread>
#include <memory>
#include "sh_p2p_tls_identity.hpp" // V79 pinned cert/account
#include "sh_p2p_tls_key_session.hpp" // V80 per TLS connection ephemeral key
#include "sh_p2p_pair_lease_v90.hpp" // developer-only coordinated 2-recipient offers

namespace SeamlessHunt::Hybrid {
class P2PTlsListener final : public QTcpServer {
public:
    explicit P2PTlsListener(QObject* parent=nullptr) : QTcpServer(parent) {}
    static constexpr int kMaxSessions=32;
    static constexpr int kMaxInputBytes=96; // V91 fixed 64-hex mTLS READY proof
    bool ConfigureLocalIdentity(const QByteArray& pin_sha256_hex,
                                const QByteArray& account,
                                P2PTlsIdentity::LiveEpoch live) {
        if (!live || !identity_.AddLocalPin(pin_sha256_hex,account)) return false;
        identity_.SetLiveEpochResolver(std::move(live));
        return true;
    }

    // V81 local operator-only selector, never set by a client's request.
    using OfferScopeResolver=std::function<std::optional<P2PLocalOfferScope>(
        const QByteArray&,const QByteArray&)>;
    bool ConfigureLocalOfferPeer(const QByteArray& peer, OfferScopeResolver resolve) {
        if(peer.isEmpty() || peer.size()>64 || !resolve || !offer_peer_.isEmpty() ||
           peer.contains('\n') || peer.contains('\r') || peer.contains('\0'))
            return false;
        offer_peer_=peer;
        offer_scope_=std::move(resolve);
        return true;
    }

    // V90 privileged local operator only: prepare BOTH halves from the
    // original Qt server's authenticated world resolver, BEFORE starting.
    // No client may choose peers or create/rekey a pair through TLS.
    bool ConfigureLocalReciprocalPairV90(
        const QByteArray& first,const QByteArray& second,
        P2PPairLeaseV90::Resolver authoritative) {
        // The original Qt server can stage a pair AFTER both players
        // have logged in, while its loopback listener is running.
        // Never mutate this QObject from the native TLS worker thread,
        // and never permit staging behind an Internet-facing listener.
        if(QThread::currentThread()!=thread() || pair_lease_.Active() ||
           (isListening() && serverAddress()!=QHostAddress::LocalHost))
            return false;
        const auto now=QDateTime::currentMSecsSinceEpoch();
        return now>0 && pair_lease_.Begin(
            first,second,std::move(authoritative),
            static_cast<std::uint64_t>(now));
    }

    // An explicitly enabled, isolated loopback smoke-test endpoint. Production
    // Internet listening requires an audited certificate-to-current-account
    // mapping, replay-safe grant issuer, throttling and client provisioning.
    bool StartLocal(const QString& server_cert_path, const QString& server_key_path,
                    const QString& trusted_client_ca_path, quint16 port=0) {
        if (isListening() || !QSslSocket::supportsSsl()) return false;
        QFile cert_file(server_cert_path),key_file(server_key_path),ca_file(trusted_client_ca_path);
        if (!cert_file.open(QIODevice::ReadOnly) ||
            !key_file.open(QIODevice::ReadOnly) ||
            !ca_file.open(QIODevice::ReadOnly))
            return false;
        const QSslCertificate cert(&cert_file,QSsl::Pem);
        const QSslKey key(&key_file,QSsl::Rsa,QSsl::Pem,QSsl::PrivateKey);
        const QSslCertificate ca(&ca_file,QSsl::Pem);
        if (cert.isNull() || key.isNull() || ca.isNull()) return false;
        QSslConfiguration config=QSslConfiguration::defaultConfiguration();
        config.setProtocol(QSsl::TlsV1_3);
        config.setPeerVerifyMode(QSslSocket::VerifyPeer);
        config.setLocalCertificate(cert);
        config.setPrivateKey(key);
        config.setCaCertificates({ca});
        config.setPeerVerifyDepth(2);
        ssl_=config;
        // Never expose this incomplete control protocol to the Internet.
        return listen(QHostAddress::LocalHost,port);
    }

    ~P2PTlsListener() override {
        close();
        const auto snapshot=clients_.values();
        for(auto* s:snapshot)s->abort();
    }
protected:
    void incomingConnection(qintptr descriptor) override {
        // Each accepted descriptor MUST be either owned by QSslSocket or
        // closed by QSslSocket when rejected. No raw/plain handler exists.
        auto* s=new QSslSocket(this);
        if(!s->setSocketDescriptor(descriptor)) {
            s->deleteLater();
            return;
        }
        if(!isListening() || clients_.size()>=kMaxSessions) {
            s->abort();s->deleteLater();return;
        }
        clients_.insert(s);
        s->setSslConfiguration(ssl_);
        const auto pending=std::make_shared<QByteArray>();
        const auto session=std::make_shared<P2PTlsKeySession>();
        QObject::connect(s,&QSslSocket::disconnected,this,[this,s] {
            clients_.remove(s);
            s->deleteLater();
        });
        QObject::connect(s,&QSslSocket::sslErrors,s,[s](const QList<QSslError>&) {
            // Qt's normal CA, expiry and client-cert verification MUST stand.
            // NEVER call ignoreSslErrors(), including in development.
            s->abort();
        });
        QObject::connect(s,&QSslSocket::encrypted,s,[s] {
            if (s->sslConfiguration().peerCertificate().isNull() ||
                s->sessionProtocol()!=QSsl::TlsV1_3)
                s->abort();
        });
        QObject::connect(s,&QSslSocket::readyRead,s,[this,s,pending,session] {
            if(!s->isEncrypted() ||
               s->sslConfiguration().peerCertificate().isNull() ||
               s->sessionProtocol()!=QSsl::TlsV1_3) {
                s->abort();return;
            }
            if(s->bytesAvailable()>kMaxInputBytes) {
                s->abort();return;
            }
            pending->append(s->readAll());
            if(pending->size()>kMaxInputBytes) {
                s->abort();return;
            }
            // Fixed protocol only. V80 application key is protected by
            // mandatory mTLS 1.3 and never logged. Still no grants or IPs.
            if(!pending->contains('\n'))return;
            if(*pending=="YT-P2P/V78 STATUS\n") {
                s->write("YT-P2P/V78 TLS_READY NO_GRANTS\n");
                s->disconnectFromHost();
            } else if (*pending=="YT-P2P/V79 BIND\n") {
                // A CA-signed client certificate alone is not a game login.
                // No client-provided account or certificate common name trusted.
                const auto bound=identity_.Resolve(s->peerCertificate());
                if(!bound) {s->abort();return;}
                s->write("YT-P2P/V79 SESSION_BOUND NO_GRANTS\n");
                s->disconnectFromHost();
            } else if (*pending=="YT-P2P/V80 BEGIN\n") {
                // V80 key bytes are sent ONLY inside this TLS 1.3 mTLS
                // connection to a pinned, currently active game account.
                const auto bound=identity_.Resolve(s->peerCertificate());
                if(!bound) {s->abort();return;}
                QByteArray key_reply;
                if(!session->Begin(*bound,key_reply)) {s->abort();return;}
                pending->clear();
                if(s->write(key_reply)!=key_reply.size()) {s->abort();return;}
                std::fill(key_reply.begin(),key_reply.end(),char(0));
            } else if (*pending=="YT-P2P/V81 OFFER\n") {
                // Only a server-provisioned peer, both currently signed-in
                // and opted into the same actual game map/world, may receive
                // a 10-second recipient-specific encrypted V75 candidate.
                const auto bound=identity_.Resolve(s->peerCertificate());
                if(!bound || !session->StillBound(identity_,s->peerCertificate()) ||
                   !offer_scope_ || offer_peer_.isEmpty()) {
                    session->Clear();s->abort();return;
                }
                const auto scoped=offer_scope_(bound->account,offer_peer_);
                if(!scoped) {session->Clear();s->abort();return;}
                QByteArray reply;
                if(!session->SealOneLocalOffer(identity_,s->peerCertificate(),
                                              *scoped,reply)) {
                    session->Clear();s->abort();return;
                }
                pending->clear();
                if(s->write(reply)!=reply.size()) {session->Clear();s->abort();return;}
                std::fill(reply.begin(),reply.end(),char(0));
            } else if (*pending=="YT-P2P/V84 OFFER\n") {
                // V85: current world and mutual P2P consent are always
                // rechecked server-side. SHG2 and legacy SHG1 cannot both
                // be issued by one V80 TLS session (shared offer_sent_).
                // This listener remains strictly 127.0.0.1 TEST-ONLY.
                const auto bound=identity_.Resolve(s->peerCertificate());
                if(!bound || !session->StillBound(identity_,s->peerCertificate()) ||
                   !offer_scope_ || offer_peer_.isEmpty()) {
                    session->Clear();s->abort();return;
                }
                const auto scoped=offer_scope_(bound->account,offer_peer_);
                if(!scoped) {session->Clear();s->abort();return;}
                QByteArray reply;
                if(!session->SealOneLocalOfferV84(identity_,s->peerCertificate(),
                                                 *scoped,reply)) {
                    session->Clear();s->abort();return;
                }
                pending->clear();
                if(s->write(reply)!=reply.size()) {
                    session->Clear();s->abort();return;
                }
                std::fill(reply.begin(),reply.end(),char(0));
            } else if (*pending=="YT-P2P/V90 OFFER\n") {
                // This intentionally cannot be requested with client-chosen
                // names, peers, endpoints, epoch or pair binding.
                const auto bound=identity_.Resolve(s->peerCertificate());
                if(!bound || !session->StillBound(identity_,s->peerCertificate())) {
                    pair_lease_.Clear();session->Clear();s->abort();return;
                }
                const qint64 stamp=QDateTime::currentMSecsSinceEpoch();
                SeamlessHunt::Hybrid::SecurePeerOfferV84 grant{};
                if(stamp<=0 || !pair_lease_.Take(
                     bound->account,bound->current_epoch,
                     static_cast<std::uint64_t>(stamp),grant)) {
                    session->Clear();s->abort();return;
                }
                QByteArray reply;
                const bool sealed=session->SealOnePairedOfferV90(
                    identity_,s->peerCertificate(),grant,
                    static_cast<std::uint64_t>(stamp),reply);
                CryptoDetail::Erase(grant.direction_key);
                if(!sealed) {
                    pair_lease_.Clear();session->Clear();s->abort();return;
                }
                pending->clear();
                if(s->write(reply)!=reply.size()) {
                    pair_lease_.Clear();session->Clear();s->abort();return;
                }
                std::fill(reply.begin(),reply.end(),char(0));
            } else if (pending->startsWith("YT-P2P/V91 READY ")) {
                // Full 32-byte proof is on the SAME verified TLS1.3
                // connection which received V90 pair half. Refuse old
                // V85/V84 standalone grants or a TLS session rebind.
                static const QByteArray prefix="YT-P2P/V91 READY ";
                const auto bound=identity_.Resolve(s->peerCertificate());
                if(!session->PairedIssued() || !bound ||
                   !session->StillBound(identity_,s->peerCertificate()) ||
                   pending->size()!=prefix.size()+64+1 ||
                   !pending->endsWith('\n')) {
                    pair_lease_.Clear();session->Clear();s->abort();return;
                }
                const auto hex=pending->mid(prefix.size(),64);
                QByteArray proof=QByteArray::fromHex(hex);
                if(proof.size()!=32 || proof.toHex()!=hex.toLower()) {
                    std::fill(proof.begin(),proof.end(),char(0));
                    pair_lease_.Clear();session->Clear();s->abort();return;
                }
                const auto stamp=QDateTime::currentMSecsSinceEpoch();
                bool both_ready=false;
                const bool accepted=stamp>0 && pair_lease_.MarkReady(
                    bound->account,bound->current_epoch,
                    std::span<const std::uint8_t>(
                        reinterpret_cast<const std::uint8_t*>(proof.constData()),
                        static_cast<std::size_t>(proof.size())),
                    static_cast<std::uint64_t>(stamp),both_ready);
                std::fill(proof.begin(),proof.end(),char(0));
                pending->clear();
                session->Clear();
                if(!accepted) {s->abort();return;}
                // STILL NO UDP DIRECT AUTHORIZATION. This acknowledges
                // mTLS possession only; both clients must also prove NAT
                // reachability AND a future server-to-both ready barrier.
                s->write(both_ready?"YT-P2P/V91 BOTH_READY\n":
                                    "YT-P2P/V91 PENDING\n");
                s->disconnectFromHost();
            } else if (*pending=="YT-P2P/V80 CHECK\n") {
                // Revocation is re-checked on this SAME TLS session: no
                // reuse if the game re-Hello/map/team/session epoch changed.
                if(!session->StillBound(identity_,s->peerCertificate())) {
                    session->Clear();
                    s->abort();return;
                }
                session->Clear();
                s->write("YT-P2P/V80 BOUND NO_GRANTS\n");
                s->disconnectFromHost();
            } else {
                s->abort();
            }
        });
        QTimer::singleShot(5000,s,[s] {
            if(s->state()!=QAbstractSocket::UnconnectedState)s->abort();
        });
        s->startServerEncryption();
    }
private:
    P2PPairLeaseV90 pair_lease_{};
    QByteArray offer_peer_{};
    OfferScopeResolver offer_scope_{};
    P2PTlsIdentity identity_{};
    QSslConfiguration ssl_{};
    QSet<QSslSocket*> clients_{};
};
} // namespace SeamlessHunt::Hybrid
