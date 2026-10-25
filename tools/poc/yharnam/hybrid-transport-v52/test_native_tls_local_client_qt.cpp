// SPDX-License-Identifier: GPL-2.0-or-later
// V83: ACTUAL native OpenSSL/LibreSSL client over real Qt server TLS 1.3.
// No Qt in the native TLS adapter itself. Temporary CI-only CA/leaf keys.
#include "sh_native_tls_local_client.hpp"
#include "sh_p2p_tls_listener.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QTimer>
#include <atomic>
#include <thread>
#include <cassert>

using namespace SeamlessHunt::Hybrid;
static QSslCertificate Certificate(const QString& path) {
    QFile f(path);
    assert(f.open(QIODevice::ReadOnly));
    QSslCertificate c(&f,QSsl::Pem);
    assert(!c.isNull());return c;
}
struct World {
    std::atomic<bool> active{true};
    NativeOfferIdentity identity{};
};
static bool Refresh(NativeOfferIdentity& id,void* ctx) noexcept {
    const auto& w=*static_cast<World*>(ctx);
    if(!w.active.load())return false;
    id=w.identity;return true;
}
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);
    assert(argc==6);
    const auto leaf=Certificate(argv[4]);
    const auto fingerprint=QCryptographicHash::hash(
        leaf.toDer(),QCryptographicHash::Sha256).toHex();
    World world;
    world.identity={
        P2PLocalOfferIssuer::AccountToken("recipient"),
        P2PLocalOfferIssuer::AccountToken("peer-A"),
        8001,93001,true};
    P2PTlsListener listener;
    assert(listener.ConfigureLocalIdentity(fingerprint,"recipient",
        [](const QByteArray& id)->quint64 {
            return id=="recipient" ? 8001 : 0;
        }));
    std::atomic<bool> both_consented{true};
    assert(listener.ConfigureLocalOfferPeer("peer-A",
        [&](const QByteArray& first,const QByteArray& second)
            ->std::optional<P2PLocalOfferScope> {
            if(!both_consented.load() || first!="recipient" || second!="peer-A")
                return std::nullopt;
            return P2PLocalOfferScope{first,second,8001,9002,93001,
                                      0x01020304u,41234,0x0a010203u,3658};
        }));
    assert(listener.StartLocal(argv[1],argv[2],argv[3],0));
    assert(listener.serverAddress()==QHostAddress::LocalHost);
    const auto port=listener.serverPort();
    NativeTlsLocalConfig config{
        argv[3],argv[4],argv[5],port
    };
    std::atomic<int> result{-1};
    std::thread worker;
    QTimer::singleShot(0,&app,[&] {
        worker=std::thread([&] {
            const auto now=[] {
                return static_cast<std::uint64_t>(QDateTime::currentMSecsSinceEpoch());
            };
            NativeSealedGrantInbox inbox;
            bool pass=NativeTlsLocalOfferClient::Request(
                config,inbox,world.identity,1,Refresh,&world,now());
            const auto* offer=inbox.PendingForNat(now());
            pass=pass && offer && offer->sender_account==world.identity.peer_account &&
                 offer->recipient_account==world.identity.self_account &&
                 offer->peer_port_nbo==qToBigEndian(quint16(41234)) &&
                 offer->peer_virtual_port_nbo==qToBigEndian(quint16(3658));
            inbox.Revoke();
            // No trusted local CA => must NEVER silently downgrade or
            // accept the server identity from the connecting peer.
            auto missing_ca=config;missing_ca.server_ca_pem="/nonexistent/ca.pem";
            pass=pass && !NativeTlsLocalOfferClient::Request(
                missing_ca,inbox,world.identity,2,Refresh,&world,now());
            auto wrong_epoch=world.identity;wrong_epoch.session_epoch++;
            pass=pass && !NativeTlsLocalOfferClient::Request(
                config,inbox,wrong_epoch,3,Refresh,&world,now());
            // A still-valid TLS identity must not override revoked consent.
            both_consented.store(false);
            pass=pass && !NativeTlsLocalOfferClient::Request(
                config,inbox,world.identity,4,Refresh,&world,now());
            both_consented.store(true);
            // A missing game-world callback always fails closed.
            world.active.store(false);
            pass=pass && !NativeTlsLocalOfferClient::Request(
                config,inbox,world.identity,5,Refresh,&world,now());
            world.active.store(true);
            // Reject an exact old TLS serial to avoid accidental reuse.
            pass=pass && !NativeTlsLocalOfferClient::Request(
                config,inbox,world.identity,1,Refresh,&world,now());
            result.store(pass?0:1);
            QMetaObject::invokeMethod(&app,[&]{app.quit();},Qt::QueuedConnection);
        });
    });
    QTimer::singleShot(18000,&app,[&]{app.exit(9);});
    const int event=app.exec();
    if(worker.joinable())worker.join();
    return event==0 && result.load()==0 ? 0 : 1;
}
