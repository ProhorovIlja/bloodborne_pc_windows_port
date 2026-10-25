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
#include <memory>
#include "sh_p2p_tls_identity.hpp" // V79 pinned cert/account
#include "sh_p2p_tls_key_session.hpp" // V80 per TLS connection ephemeral key

namespace SeamlessHunt::Hybrid {
class P2PTlsListener final : public QTcpServer {
public:
    explicit P2PTlsListener(QObject* parent=nullptr) : QTcpServer(parent) {}
    static constexpr int kMaxSessions=32;
    static constexpr int kMaxInputBytes=64;
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
    QByteArray offer_peer_{};
    OfferScopeResolver offer_scope_{};
    P2PTlsIdentity identity_{};
    QSslConfiguration ssl_{};
    QSet<QSslSocket*> clients_{};
};
} // namespace SeamlessHunt::Hybrid
