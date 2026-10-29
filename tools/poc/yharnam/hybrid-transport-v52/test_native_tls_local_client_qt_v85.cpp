// SPDX-License-Identifier: GPL-2.0-or-later
// V85: ACTUAL native OpenSSL/LibreSSL client over real Qt server TLS 1.3.
// No Qt in the native TLS adapter itself. Temporary CI-only CA/leaf keys.
#include "sh_native_tls_local_client_v85.hpp"
#include "sh_p2p_tls_listener.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QTimer>
#include <atomic>
#include <thread>
#include <cassert>
#include <cstdio>
#include <cstdio>

using namespace SeamlessHunt::Hybrid;
static QSslCertificate Certificate(const QString& path) {
    QFile f(path);
    assert(f.open(QIODevice::ReadOnly));
    QSslCertificate c(&f,QSsl::Pem);
    assert(!c.isNull());return c;
}
struct World {
    std::atomic<bool> active{true};
    NativeOfferIdentityV84 identity{};
};
static bool Refresh(NativeOfferIdentityV84& id,void* ctx) noexcept {
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
    const auto self=P2PFullIdentityIssuerV84::AccountDigest("recipient");
    const auto peer=P2PFullIdentityIssuerV84::AccountDigest("peer-A");
    assert(self && peer);
    world.identity={*self,*peer,8001,93001,true};
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
            NativeSealedGrantInboxV84 inbox;
            std::uint8_t stage=0;
            bool pass=NativeTlsLocalOfferClientV85::Request(
                config,inbox,world.identity,1,Refresh,&world,now(),&stage);
            std::fprintf(stderr,"V85 stage local TLS+offer: %s (checkpoint %u)\n",
                         pass?"PASS":"FAIL",unsigned(stage));
            std::fprintf(stderr,"V85 first_request=%d pending=%d\\n",pass?1:0,inbox.IsPending()?1:0);
            const auto* offer=inbox.PendingForNat(now());
            std::fprintf(stderr,"V85 stage pending native offer: %s\n",offer?"PASS":"FAIL");
            pass=pass && offer && offer->sender_account==world.identity.peer_account &&
                 offer->recipient_account==world.identity.self_account &&
                 offer->peer_port_nbo==qToBigEndian(quint16(41234)) &&
                 offer->peer_virtual_port_nbo==qToBigEndian(quint16(3658));
            inbox.Revoke();
            // No trusted local CA => must NEVER silently downgrade or
            // accept the server identity from the connecting peer.
            auto missing_ca=config;missing_ca.server_ca_pem="/nonexistent/ca.pem";
            const bool wrong_ca_denied=!NativeTlsLocalOfferClientV85::Request(
                missing_ca,inbox,world.identity,2,Refresh,&world,now());
            std::fprintf(stderr,"V85 stage missing CA denial: %s\n",wrong_ca_denied?"PASS":"FAIL");
            pass=pass && wrong_ca_denied;
            auto wrong_epoch=world.identity;wrong_epoch.session_epoch++;
            const bool wrong_epoch_denied=!NativeTlsLocalOfferClientV85::Request(
                config,inbox,wrong_epoch,3,Refresh,&world,now());
            std::fprintf(stderr,"V85 stage stale epoch denial: %s\n",wrong_epoch_denied?"PASS":"FAIL");
            pass=pass && wrong_epoch_denied;
            // A still-valid TLS identity must not override revoked consent.
            both_consented.store(false);
            const bool no_consent_denied=!NativeTlsLocalOfferClientV85::Request(
                config,inbox,world.identity,4,Refresh,&world,now());
            std::fprintf(stderr,"V85 stage peer optout denial: %s\n",no_consent_denied?"PASS":"FAIL");
            pass=pass && no_consent_denied;
            both_consented.store(true);
            // A missing game-world callback always fails closed.
            world.active.store(false);
            const bool no_world_denied=!NativeTlsLocalOfferClientV85::Request(
                config,inbox,world.identity,5,Refresh,&world,now());
            std::fprintf(stderr,"V85 stage missing world denial: %s\n",no_world_denied?"PASS":"FAIL");
            pass=pass && no_world_denied;
            world.active.store(true);
            // Reject an exact old TLS serial to avoid accidental reuse.
            const bool replay_denied=!NativeTlsLocalOfferClientV85::Request(
                config,inbox,world.identity,1,Refresh,&world,now());
            std::fprintf(stderr,"V85 stage old serial denial: %s\n",replay_denied?"PASS":"FAIL");
            pass=pass && replay_denied;
            std::fprintf(stderr,"V85 final result=%d\\n",pass?1:0);
            result.store(pass?0:1);
            QMetaObject::invokeMethod(&app,[&]{app.quit();},Qt::QueuedConnection);
        });
    });
    QTimer::singleShot(18000,&app,[&]{app.exit(9);});
    const int event=app.exec();
    if(worker.joinable())worker.join();
    std::fprintf(stderr,"V85 event=%d result=%d\\n",event,result.load());
    return event==0 && result.load()==0 ? 0 : 1;
}
