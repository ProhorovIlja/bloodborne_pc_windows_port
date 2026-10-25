// SPDX-License-Identifier: GPL-2.0-or-later
// V80 actual TLS1.3 Qt key handoff, uniqueness, epoch recheck and
// second BEGIN denial. Throwaway CI CA/cert, NO production accounts.
#include "sh_p2p_tls_listener.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QSslSocket>
#include <QTimer>
#include <cassert>

static QSslCertificate Cert(const QString& name) {
    QFile f(name);assert(f.open(QIODevice::ReadOnly));
    QSslCertificate c(&f,QSsl::Pem);assert(!c.isNull());return c;
}
static QSslKey Key(const QString& name) {
    QFile f(name);assert(f.open(QIODevice::ReadOnly));
    QSslKey k(&f,QSsl::Rsa,QSsl::Pem,QSsl::PrivateKey);
    assert(!k.isNull());return k;
}
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);assert(argc==6);
    const auto client=Cert(argv[4]);
    const auto fingerprint=QCryptographicHash::hash(
        client.toDer(),QCryptographicHash::Sha256).toHex();
    quint64 epoch=711;
    SeamlessHunt::Hybrid::P2PTlsListener listener;
    assert(listener.ConfigureLocalIdentity(fingerprint,"v80-player",
        [&](const QByteArray& id)->quint64 {
            return id=="v80-player" ? epoch : 0;
        }));
    assert(listener.StartLocal(argv[1],argv[2],argv[3],0));
    assert(listener.serverAddress()==QHostAddress::LocalHost);
    QSslConfiguration cfg=QSslConfiguration::defaultConfiguration();
    cfg.setProtocol(QSsl::TlsV1_3);
    cfg.setPeerVerifyMode(QSslSocket::VerifyPeer);
    cfg.setCaCertificates({Cert(argv[3])});
    cfg.setLocalCertificate(client);
    cfg.setPrivateKey(Key(argv[5]));

    QSslSocket first,revoked,replayed;
    first.setSslConfiguration(cfg);
    revoked.setSslConfiguration(cfg);
    replayed.setSslConfiguration(cfg);
    QByteArray original_key;
    int phase=0;
    QByteArray first_buf,second_buf,replay_buf;
    QObject::connect(&first,&QSslSocket::encrypted,&app,[&] {
        assert(first.sessionProtocol()==QSsl::TlsV1_3);
        first.write("YT-P2P/V80 BEGIN\n");
    });
    QObject::connect(&first,&QSslSocket::readyRead,&app,[&] {
        first_buf+=first.readAll();
        if(!first_buf.endsWith('\n'))return;
        if(phase==0) {
            if(!first_buf.startsWith("YT-P2P/V80 KEY ") ||
               first_buf.size()!=17+64+1) {app.exit(2);return;}
            original_key=first_buf.mid(17,64);
            if(QByteArray::fromHex(original_key).size()!=32) {app.exit(3);return;}
            first_buf.clear();phase=1;
            first.write("YT-P2P/V80 CHECK\n");
        } else {
            if(first_buf!="YT-P2P/V80 BOUND NO_GRANTS\n") {
                app.exit(4);return;
            }
            phase=2;
        }
    });
    QObject::connect(&first,&QSslSocket::disconnected,&app,[&] {
        if(phase!=2) {app.exit(5);return;}
        phase=3;
        revoked.connectToHostEncrypted("127.0.0.1",listener.serverPort());
    });
    QObject::connect(&revoked,&QSslSocket::encrypted,&app,[&] {
        revoked.write("YT-P2P/V80 BEGIN\n");
    });
    QObject::connect(&revoked,&QSslSocket::readyRead,&app,[&] {
        second_buf+=revoked.readAll();
        if(!second_buf.endsWith('\n'))return;
        if(phase!=3 ||
           !second_buf.startsWith("YT-P2P/V80 KEY ") ||
           second_buf.size()!=17+64+1 ||
           second_buf.mid(17,64)==original_key) {app.exit(6);return;}
        phase=4;
        epoch=712; // changing server-owned game link generation revokes key
        revoked.write("YT-P2P/V80 CHECK\n");
    });
    QObject::connect(&revoked,&QSslSocket::disconnected,&app,[&] {
        if(phase!=4) {app.exit(7);return;}
        phase=5; // no success response was delivered
        replayed.connectToHostEncrypted("127.0.0.1",listener.serverPort());
    });
    QObject::connect(&replayed,&QSslSocket::encrypted,&app,[&] {
        replayed.write("YT-P2P/V80 BEGIN\n");
    });
    QObject::connect(&replayed,&QSslSocket::readyRead,&app,[&] {
        replay_buf+=replayed.readAll();
        if(!replay_buf.endsWith('\n'))return;
        if(phase!=5 ||
           !replay_buf.startsWith("YT-P2P/V80 KEY ")) {app.exit(8);return;}
        phase=6;
        replayed.write("YT-P2P/V80 BEGIN\n"); // must reject second key
    });
    QObject::connect(&replayed,&QSslSocket::disconnected,&app,[&] {
        if(phase!=6) {app.exit(9);return;}
        phase=7;app.quit();
    });
    QTimer::singleShot(8000,&app,[&]{app.exit(10);});
    first.connectToHostEncrypted("127.0.0.1",listener.serverPort());
    const int result=app.exec();
    std::fill(original_key.begin(),original_key.end(),char(0));
    return result==0 && phase==7 ? 0 : 1;
}
