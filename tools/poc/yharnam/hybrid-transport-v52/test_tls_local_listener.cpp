// SPDX-License-Identifier: GPL-2.0-or-later
// Actual Qt TLS 1.3 loopback integration with throwaway CI CA and leaf keys.
// Never uses live account data or production server keys.
#include "sh_p2p_tls_listener.hpp"
#include <QCoreApplication>
#include <QFile>
#include <QHostAddress>
#include <QSslConfiguration>
#include <QSslKey>
#include <QSslSocket>
#include <QTimer>
#include <cassert>

static QSslCertificate LoadCert(const QString& filename) {
    QFile f(filename);
    assert(f.open(QIODevice::ReadOnly));
    const QSslCertificate result(&f,QSsl::Pem);
    assert(!result.isNull());
    return result;
}
static QSslKey LoadKey(const QString& filename) {
    QFile f(filename);
    assert(f.open(QIODevice::ReadOnly));
    const QSslKey result(&f,QSsl::Rsa,QSsl::Pem,QSsl::PrivateKey);
    assert(!result.isNull());
    return result;
}
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);
    assert(argc==6);
    using SeamlessHunt::Hybrid::P2PTlsListener;
    P2PTlsListener server;
    assert(!server.StartLocal({},{},{},0)); // fails closed with no secrets
    assert(server.StartLocal(argv[1],argv[2],argv[3],0));
    assert(!server.StartLocal(argv[1],argv[2],argv[3],0)); // no double bind
    assert(server.serverAddress()==QHostAddress::LocalHost);
    assert(server.serverPort()!=0);
    QSslConfiguration cfg=QSslConfiguration::defaultConfiguration();
    cfg.setProtocol(QSsl::TlsV1_3);
    cfg.setCaCertificates({LoadCert(argv[3])});
    cfg.setLocalCertificate(LoadCert(argv[4]));
    cfg.setPrivateKey(LoadKey(argv[5]));
    cfg.setPeerVerifyMode(QSslSocket::VerifyPeer);
    QSslSocket valid;
    valid.setSslConfiguration(cfg);
    bool accepted=false,negative_denied=false;
    QObject::connect(&valid,&QSslSocket::encrypted,&app,[&] {
        assert(valid.sessionProtocol()==QSsl::TlsV1_3);
        valid.write("YT-P2P/V78 STATUS\n");
    });
    QSslSocket no_cert;
    QObject::connect(&valid,&QSslSocket::readyRead,&app,[&] {
        const auto resp=valid.readAll();
        if(resp!="YT-P2P/V78 TLS_READY NO_GRANTS\n") {
            app.exit(2);return;
        }
        accepted=true;
        QSslConfiguration bad=QSslConfiguration::defaultConfiguration();
        bad.setProtocol(QSsl::TlsV1_3);
        bad.setCaCertificates({LoadCert(argv[3])});
        bad.setPeerVerifyMode(QSslSocket::VerifyPeer);
        no_cert.setSslConfiguration(bad);
        no_cert.connectToHostEncrypted("127.0.0.1",server.serverPort());
    });
    QObject::connect(&no_cert,&QSslSocket::readyRead,&app,[&] {
        // A TLS client without a CA-approved certificate must not even
        // receive the nonsecret readiness response, much less a grant.
        if(!no_cert.readAll().isEmpty())app.exit(3);
    });
    QObject::connect(&no_cert,&QSslSocket::disconnected,&app,[&] {
        negative_denied=true;app.quit();
    });
    QObject::connect(&no_cert,&QSslSocket::sslErrors,&app,[&](const QList<QSslError>&) {
        negative_denied=true;
        no_cert.abort();
        app.quit();
    });
    QTimer::singleShot(8500,&app,[&] {app.exit(4);});
    valid.connectToHostEncrypted("127.0.0.1",server.serverPort());
    const int event_result=app.exec();
    if(event_result!=0 || !accepted || !negative_denied)return 1;
    return 0;
}
