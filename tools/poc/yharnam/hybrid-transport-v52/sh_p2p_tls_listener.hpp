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

namespace SeamlessHunt::Hybrid {
class P2PTlsListener final : public QTcpServer {
public:
    explicit P2PTlsListener(QObject* parent=nullptr) : QTcpServer(parent) {}
    static constexpr int kMaxSessions=32;
    static constexpr int kMaxInputBytes=64;

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
        for(auto* s:clients_)s->abort();
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
        auto* pending=new QByteArray;
        QObject::connect(s,&QSslSocket::disconnected,s,[this,s,pending] {
            clients_.remove(s);
            delete pending;
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
        QObject::connect(s,&QSslSocket::readyRead,s,[s,pending] {
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
            // Only a fixed, non-secret probe is supported in V78.
            // No user names, IPs, game grants, credentials or keys.
            if(!pending->contains('\n'))return;
            if(*pending=="YT-P2P/V78 STATUS\n") {
                s->write("YT-P2P/V78 TLS_READY NO_GRANTS\n");
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
    QSslConfiguration ssl_{};
    QSet<QSslSocket*> clients_{};
};
} // namespace SeamlessHunt::Hybrid
