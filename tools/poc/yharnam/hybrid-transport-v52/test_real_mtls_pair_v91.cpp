// SPDX-License-Identifier: GPL-2.0-or-later
// V91: real Qt TLS1.3 server, two SEPARATE pinned native TLS clients,
// single server-authorized one-use SHG2 pair with reciprocal KDF.
#include "sh_p2p_tls_listener.hpp"
#include "sh_native_tls_local_client_v91.hpp"
#include "sh_pair_key_schedule_v89.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QSslConfiguration>
#include <QSslKey>
#include <QSslSocket>
#include <QTimer>
#include <atomic>
#include <thread>
#include <cassert>
#include <cstdint>
#include <cstdio>
using namespace SeamlessHunt::Hybrid;
static QSslCertificate Leaf(const QString& path) {
    QFile f(path);
    assert(f.open(QIODevice::ReadOnly));
    QSslCertificate cert(&f,QSsl::Pem);
    assert(!cert.isNull());return cert;
}
static QByteArray Pin(const QString& path) {
    return QCryptographicHash::hash(
        Leaf(path).toDer(),QCryptographicHash::Sha256).toHex();
}
// V101: exercise the actual Qt TLS listener, not only P2PPairLease methods.
// A valid certificate on a fresh session lacking V80+V90 ownership must
// NOT be able to abort the already staged A/B grant via OFFER or READY.
static bool RejectUnpairedCommand(const QString& ca_path,
                                  const QString& cert_path,
                                  const QString& key_path,
                                  quint16 port,const QByteArray& cmd) {
    QFile key_file(key_path);
    if(!key_file.open(QIODevice::ReadOnly))return false;
    const QSslKey key(&key_file,QSsl::Rsa,QSsl::Pem,QSsl::PrivateKey);
    if(key.isNull())return false;
    QSslConfiguration cfg=QSslConfiguration::defaultConfiguration();
    cfg.setProtocol(QSsl::TlsV1_3);
    cfg.setCaCertificates({Leaf(ca_path)});
    cfg.setLocalCertificate(Leaf(cert_path));
    cfg.setPrivateKey(key);
    cfg.setPeerVerifyMode(QSslSocket::VerifyPeer);
    QSslSocket socket;
    socket.setSslConfiguration(cfg);
    socket.connectToHostEncrypted("127.0.0.1",port);
    if(!socket.waitForEncrypted(4000))return false;
    if(socket.write(cmd)!=cmd.size() || !socket.waitForBytesWritten(4000))
        return false;
    const bool disconnected=socket.waitForDisconnected(4000) ||
                            socket.state()==QAbstractSocket::UnconnectedState;
    return disconnected && socket.bytesAvailable()==0;
}
struct Identity {
    NativeOfferIdentityV84 current{};
    std::atomic<bool> live{true};
};
static bool Refresh(NativeOfferIdentityV84& out,void* ptr) noexcept {
    const auto& state=*static_cast<Identity*>(ptr);
    if(!state.live.load())return false;
    out=state.current;return true;
}
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);
    assert(argc==8);
    const auto a=P2PFullIdentityIssuerV84::AccountDigest("hunter-A");
    const auto b=P2PFullIdentityIssuerV84::AccountDigest("hunter-B");
    assert(a && b);
    Identity first{{*a,*b,101,303,true}};
    Identity second{{*b,*a,202,303,true}};
    std::atomic<bool> consent{true};
    std::atomic<bool> world_ok{true};
    P2PTlsListener listener;
    auto live_epoch=[&](const QByteArray& account)->quint64 {
        if(!world_ok.load())return 0;
        if(account=="hunter-A")return 101;
        if(account=="hunter-B")return 202;
        return 0;
    };
    assert(listener.ConfigureLocalIdentity(Pin(argv[4]),"hunter-A",live_epoch));
    assert(listener.ConfigureLocalIdentity(Pin(argv[6]),"hunter-B",live_epoch));
    auto scoped=[&](const QByteArray& recipient,const QByteArray& peer)
         ->std::optional<P2PLocalOfferScope> {
        if(!consent.load() || !world_ok.load())return std::nullopt;
        if(recipient=="hunter-A" && peer=="hunter-B")
            return P2PLocalOfferScope{
                recipient,peer,101,202,303,0x7f000001u,42442,
                0x0a010002u,31102};
        if(recipient=="hunter-B" && peer=="hunter-A")
            return P2PLocalOfferScope{
                recipient,peer,202,101,303,0x7f000001u,42441,
                0x0a010001u,31101};
        return std::nullopt;
    };
    assert(listener.StartLocal(argv[1],argv[2],argv[3],0));
    assert(listener.serverAddress()==QHostAddress::LocalHost);
    // Pair must be configurable only from the original Qt server event
    // thread AFTER the gamers are actually signed in, not at startup.
    assert(listener.ConfigureLocalReciprocalPairV90(
        "hunter-A","hunter-B",scoped));
    // Never replace a live, partially delivered or READY-pending pair.
    assert(!listener.ConfigureLocalReciprocalPairV90(
        "hunter-A","hunter-B",scoped));
    const auto port=listener.serverPort();
    NativeTlsLocalConfig config_a{argv[3],argv[4],argv[5],port};
    NativeTlsLocalConfig config_b{argv[3],argv[6],argv[7],port};
    std::atomic<int> exit_code{-1};
    std::thread worker;
    QTimer::singleShot(0,&app,[&] {
        worker=std::thread([&] {
            const auto now=[] {
                return static_cast<std::uint64_t>(QDateTime::currentMSecsSinceEpoch());
            };
            NativeSealedGrantInboxV84 box_a,box_b;
            SecurePeerOfferV84 grant_a{},grant_b{};
            bool ready_a=false,ready_b=false;
            // A fresh but verified mTLS socket has not received a paired
            // grant. Neither a forged READY nor an OFFER without V80 BEGIN
            // can revoke the separate waiting A/B lease.
            bool good=RejectUnpairedCommand(
                argv[3],argv[4],argv[5],port,
                "YT-P2P/V91 READY "+QByteArray(64,'a')+"\\n");
            good=good && RejectUnpairedCommand(
                argv[3],argv[4],argv[5],port,"YT-P2P/V90 OFFER\\n");
            std::fprintf(stderr,"V101 real TLS unissued OFFER/READY denial: %s\\n",
                         good?"PASS":"FAIL");
            good=good && NativeTlsLocalOfferClientV91::Request(
                config_a,box_a,first.current,1,Refresh,&first,now(),ready_a);
            good=good && !ready_a;
            const auto* pa=box_a.PendingForNat(now());
            good=good && pa;
            if(pa)grant_a=*pa;
            std::fprintf(stderr,"V91 client A actual TLS SHG2: %s\n",good?"PASS":"FAIL");
            if(good) {
                good=NativeTlsLocalOfferClientV91::Request(
                    config_b,box_b,second.current,1,Refresh,&second,now(),ready_b);
                good=good && ready_b;
                const auto* pb=box_b.PendingForNat(now());
                good=good && pb;
                if(pb)grant_b=*pb;
            }
            std::fprintf(stderr,"V91 client B actual TLS SHG2: %s\n",good?"PASS":"FAIL");
            if(good) {
                good=grant_a.pair_binding && grant_a.pair_binding==grant_b.pair_binding &&
                     grant_a.direction_key==grant_b.direction_key &&
                     grant_a.sender_account==grant_b.recipient_account &&
                     grant_b.sender_account==grant_a.recipient_account &&
                     grant_a.session_epoch==101 && grant_b.session_epoch==202 &&
                     grant_a.world_revision==303 && grant_b.world_revision==303;
            }
            std::array<std::uint8_t,32> ab{},b_rx{},ba{},a_rx{},game{};
            if(good) {
                good=PairKeyScheduleV89::Derive(grant_a,true,
                     PairKeyPurposeV89::NatProbe,now(),ab) &&
                     PairKeyScheduleV89::Derive(grant_b,false,
                     PairKeyPurposeV89::NatProbe,now(),b_rx) &&
                     PairKeyScheduleV89::Derive(grant_b,true,
                     PairKeyPurposeV89::NatProbe,now(),ba) &&
                     PairKeyScheduleV89::Derive(grant_a,false,
                     PairKeyPurposeV89::NatProbe,now(),a_rx) &&
                     PairKeyScheduleV89::Derive(grant_a,true,
                     PairKeyPurposeV89::GameData,now(),game) &&
                     ab==b_rx && ba==a_rx && ab!=ba && ab!=game;
            }
            std::fprintf(stderr,"V91 pair-matched probe/game keys: %s\n",good?"PASS":"FAIL");
            // A third TLS connection cannot mint another ticket from
            // either recipient's single-use world-authorized pair.
            NativeSealedGrantInboxV84 replay_box;
            bool replay_ready=false;
            const bool replay_denied=!NativeTlsLocalOfferClientV91::Request(
                config_a,replay_box,first.current,2,Refresh,&first,now(),replay_ready);
            good=good && !replay_ready;
            good=good && replay_denied && !replay_box.IsPending();
            std::fprintf(stderr,"V91 third-recipient replay denied: %s\n",
                         replay_denied?"PASS":"FAIL");
            CryptoDetail::Erase(grant_a.direction_key);
            CryptoDetail::Erase(grant_b.direction_key);
            CryptoDetail::Erase(ab);CryptoDetail::Erase(b_rx);
            CryptoDetail::Erase(ba);CryptoDetail::Erase(a_rx);
            CryptoDetail::Erase(game);
            box_a.Revoke();box_b.Revoke();
            exit_code.store(good?0:1);
            QMetaObject::invokeMethod(&app,[&]{app.quit();},Qt::QueuedConnection);
        });
    });
    QTimer::singleShot(16000,&app,[&]{app.exit(9);});
    const int event=app.exec();
    if(worker.joinable())worker.join();
    return event==0 && exit_code.load()==0 ? 0:1;
}
