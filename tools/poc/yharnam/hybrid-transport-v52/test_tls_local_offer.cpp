// SPDX-License-Identifier: GPL-2.0-or-later
// V81: actual Qt mTLS1.3 socket -> V80 key -> V75 AES-GCM SHG1 grant.
// Test-only game world callback. Original real Qt world is tested separately.
#include "sh_p2p_tls_listener.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QFile>
#include <QSslSocket>
#include <QTimer>
#include <cassert>
#include <array>
#include <span>
using namespace SeamlessHunt::Hybrid;
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
    QCoreApplication app(argc,argv);assert(argc==6);
    const auto cert=Cert(argv[4]);
    const auto fingerprint=QCryptographicHash::hash(
        cert.toDer(),QCryptographicHash::Sha256).toHex();
    quint64 game_epoch=8001;
    bool peer_opted_in=true;
    P2PTlsListener server;
    assert(server.ConfigureLocalIdentity(fingerprint,"recipient",
        [&](const QByteArray& name)->quint64 {
            return name=="recipient" ? game_epoch : 0;
        }));
    assert(server.ConfigureLocalOfferPeer("peer-A",
        [&](const QByteArray& a,const QByteArray& b)
            ->std::optional<P2PLocalOfferScope> {
            if(!peer_opted_in || a!="recipient" || b!="peer-A")
                return std::nullopt;
            return P2PLocalOfferScope{a,b,game_epoch,9002,93001,
                0x01020304U,41234,0x0A010203U,3658};
        }));
    assert(!server.ConfigureLocalOfferPeer("changed-peer",
        [](const QByteArray&,const QByteArray&)
             ->std::optional<P2PLocalOfferScope> {return std::nullopt;}));
    // V81: no client-supplied online_id/epoch may ever pass the issuer.
    const P2PLocalOfferScope trusted_scope{
        "recipient","peer-A",game_epoch,9002,93001,
        0x01020304U,41234,0x0A010203U,3658
    };
    SecurePeerOffer malformed{};
    assert(!P2PLocalOfferIssuer::Prepare(trusted_scope,"attacker",game_epoch,
                                        120000,malformed));
    assert(!P2PLocalOfferIssuer::Prepare(trusted_scope,"recipient",game_epoch+1,
                                        120000,malformed));
    auto changed=trusted_scope;
    changed.recipient="peer-A";
    assert(!P2PLocalOfferIssuer::Prepare(changed,"recipient",game_epoch,
                                        120000,malformed));
    changed=trusted_scope;changed.world_revision=0;
    assert(!P2PLocalOfferIssuer::Prepare(changed,"recipient",game_epoch,
                                        120000,malformed));
    changed=trusted_scope;changed.physical_port_host=0;
    assert(!P2PLocalOfferIssuer::Prepare(changed,"recipient",game_epoch,
                                        120000,malformed));
    assert(server.StartLocal(argv[1],argv[2],argv[3],0));
    assert(server.serverAddress()==QHostAddress::LocalHost);

    QSslConfiguration cfg=QSslConfiguration::defaultConfiguration();
    cfg.setProtocol(QSsl::TlsV1_3);
    cfg.setPeerVerifyMode(QSslSocket::VerifyPeer);
    cfg.setCaCertificates({Cert(argv[3])});
    cfg.setLocalCertificate(cert);
    cfg.setPrivateKey(Key(argv[5]));
    QSslSocket first,denied;
    first.setSslConfiguration(cfg);denied.setSslConfiguration(cfg);
    QByteArray incoming,secret;
    int phase=0;
    QObject::connect(&first,&QSslSocket::encrypted,&app,[&] {
        first.write("YT-P2P/V80 BEGIN\n");
    });
    QObject::connect(&first,&QSslSocket::readyRead,&app,[&] {
        incoming+=first.readAll();
        if(!incoming.endsWith('\n'))return;
        if(phase==0) {
            const QByteArray prefix="YT-P2P/V80 KEY ";
            if(!incoming.startsWith(prefix) ||
               incoming.size()!=prefix.size()+65){app.exit(2);return;}
            secret=QByteArray::fromHex(incoming.mid(prefix.size(),64));
            if(secret.size()!=32){app.exit(3);return;}
            phase=1;incoming.clear();
            first.write("YT-P2P/V81 OFFER\n");
        } else if(phase==1) {
            const QByteArray prefix="YT-P2P/V81 OFFER ";
            if(!incoming.startsWith(prefix) ||
               incoming.size()!=prefix.size()+
                   2*static_cast<int>(SecureOfferDetail::kWireBytes)+1){
                app.exit(4);return;
            }
            const auto wire=QByteArray::fromHex(
                incoming.mid(prefix.size(),incoming.size()-prefix.size()-1));
            if(wire.size()!=static_cast<int>(SecureOfferDetail::kWireBytes)) {
                app.exit(5);return;
            }
            SealedPeerOffers client;
            auto secret_span=std::span<const std::uint8_t>(
                reinterpret_cast<const std::uint8_t*>(secret.constData()),
                static_cast<std::size_t>(secret.size()));
            if(!client.InstallChannelKey(secret_span)){app.exit(6);return;}
            const auto encrypted=std::span<const std::uint8_t>(
                reinterpret_cast<const std::uint8_t*>(wire.constData()),
                static_cast<std::size_t>(wire.size()));
            const auto recipient=P2PLocalOfferIssuer::AccountToken("recipient");
            const auto peer=P2PLocalOfferIssuer::AccountToken("peer-A");
            SecurePeerOffer accepted{};
            auto now=static_cast<std::uint64_t>(QDateTime::currentMSecsSinceEpoch());
            if(!client.Open(encrypted,recipient,game_epoch,93001,now,accepted) ||
               accepted.sender_account!=peer ||
               accepted.recipient_account!=recipient ||
               accepted.peer_ipv4_nbo!=qToBigEndian(quint32(0x01020304)) ||
               accepted.peer_port_nbo!=qToBigEndian(quint16(41234)) ||
               accepted.peer_virtual_ipv4_nbo!=qToBigEndian(quint32(0x0A010203)) ||
               accepted.peer_virtual_port_nbo!=qToBigEndian(quint16(3658)) ||
               !SecureOfferDetail::Valid(accepted,now)) {app.exit(7);return;}
            CryptoDetail::Erase(accepted.direction_key);
            if(client.Open(encrypted,recipient,game_epoch,93001,now,accepted)) {
                app.exit(8);return; // replay must be refused
            }
            auto corrupted=wire;corrupted[40]^=1;
            const auto tampered=std::span<const std::uint8_t>(
                reinterpret_cast<const std::uint8_t*>(corrupted.constData()),
                static_cast<std::size_t>(corrupted.size()));
            if(client.Open(tampered,recipient,game_epoch,93001,now,accepted)) {
                app.exit(9);return;
            }
            phase=2;incoming.clear();
            first.write("YT-P2P/V81 OFFER\n"); // same socket replay denied
        } else {app.exit(10);}
    });
    QObject::connect(&first,&QSslSocket::disconnected,&app,[&] {
        if(phase!=2){app.exit(11);return;}
        phase=3;peer_opted_in=false; // second client sees revoked consent
        denied.connectToHostEncrypted("127.0.0.1",server.serverPort());
    });
    QByteArray second_incoming;
    QObject::connect(&denied,&QSslSocket::encrypted,&app,[&] {
        denied.write("YT-P2P/V80 BEGIN\n");
    });
    QObject::connect(&denied,&QSslSocket::readyRead,&app,[&] {
        second_incoming+=denied.readAll();
        if(!second_incoming.endsWith('\n'))return;
        if(phase==3 &&
           second_incoming.startsWith("YT-P2P/V80 KEY ")) {
            phase=4;second_incoming.clear();
            denied.write("YT-P2P/V81 OFFER\n"); // revoked pair MUST deny
        } else app.exit(12);
    });
    QObject::connect(&denied,&QSslSocket::disconnected,&app,[&] {
        if(phase!=4){app.exit(13);return;}
        phase=5;app.quit();
    });
    QTimer::singleShot(8500,&app,[&]{app.exit(14);});
    first.connectToHostEncrypted("127.0.0.1",server.serverPort());
    const int result=app.exec();
    std::fill(secret.begin(),secret.end(),char(0));
    return (result==0 && phase==5)?0:1;
}
