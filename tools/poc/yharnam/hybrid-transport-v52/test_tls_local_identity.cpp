// SPDX-License-Identifier: GPL-2.0-or-later
// V79 real Qt mTLS handshake + exact SHA256 leaf fingerprint + revocation.
#include "sh_p2p_tls_listener.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QSslSocket>
#include <QTimer>
#include <cassert>

static QSslCertificate Cert(const QString& f) {
    QFile file(f);assert(file.open(QIODevice::ReadOnly));
    QSslCertificate c(&file,QSsl::Pem);assert(!c.isNull());return c;
}
static QSslKey Key(const QString& f) {
    QFile file(f);assert(file.open(QIODevice::ReadOnly));
    QSslKey k(&file,QSsl::Rsa,QSsl::Pem,QSsl::PrivateKey);
    assert(!k.isNull());return k;
}
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);
    assert(argc==6);
    const auto client=Cert(argv[4]);
    const QByteArray fingerprint=QCryptographicHash::hash(
        client.toDer(),QCryptographicHash::Sha256).toHex();
    bool live=true;
    SeamlessHunt::Hybrid::P2PTlsListener server;
    assert(!server.ConfigureLocalIdentity("zz", "test-account",
               [&](const QByteArray&){return quint64(9);}));
    assert(server.ConfigureLocalIdentity(fingerprint,"test-account",
        [&](const QByteArray& id)->quint64 {
            return live && id=="test-account" ? 711 : 0;
        }));
    assert(!server.ConfigureLocalIdentity(fingerprint,"evil-account",
        [&](const QByteArray&)->quint64{return 711;}));
    assert(server.StartLocal(argv[1],argv[2],argv[3],0));
    QSslConfiguration cfg=QSslConfiguration::defaultConfiguration();
    cfg.setProtocol(QSsl::TlsV1_3);
    cfg.setPeerVerifyMode(QSslSocket::VerifyPeer);
    cfg.setCaCertificates({Cert(argv[3])});
    cfg.setLocalCertificate(client);
    cfg.setPrivateKey(Key(argv[5]));
    QSslSocket first,second;
    first.setSslConfiguration(cfg);
    second.setSslConfiguration(cfg);
    bool first_accepted=false,revoked_denied=false;
    QObject::connect(&first,&QSslSocket::encrypted,&app,[&] {
        first.write("YT-P2P/V79 BIND\n");
    });
    QObject::connect(&first,&QSslSocket::readyRead,&app,[&] {
        const auto value=first.readAll();
        if(value!="YT-P2P/V79 SESSION_BOUND NO_GRANTS\n") {app.exit(2);return;}
        first_accepted=true;
        live=false; // current game link disconnected since previous TLS
        second.connectToHostEncrypted("127.0.0.1",server.serverPort());
    });
    QObject::connect(&second,&QSslSocket::encrypted,&app,[&] {
        second.write("YT-P2P/V79 BIND\n");
    });
    QObject::connect(&second,&QSslSocket::readyRead,&app,[&] {
        if(!second.readAll().isEmpty())app.exit(3);
    });
    QObject::connect(&second,&QSslSocket::disconnected,&app,[&] {
        revoked_denied=true;
        app.quit();
    });
    QTimer::singleShot(8500,&app,[&]{app.exit(4);});
    first.connectToHostEncrypted("127.0.0.1",server.serverPort());
    const auto res=app.exec();
    return (res==0&&first_accepted&&revoked_denied)?0:1;
}
