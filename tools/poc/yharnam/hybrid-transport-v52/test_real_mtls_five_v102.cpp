// SPDX-License-Identifier: GPL-2.0-or-later
// V102: five distinct native hunters, original Qt TLS1.3 server event loop,
// ten cert-pinned SHG2 exchanges; no cross-team pair selector. Direct OFF.
#include "sh_p2p_tls_listener.hpp"
#include "sh_native_tls_local_client_v91.hpp"
#include "sh_native_tls_pair_list_v102.hpp"
#include "sh_native_team_grant_slots_v103.hpp"
#include "sh_pair_key_schedule_v89.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QSslConfiguration>
#include <QSslKey>
#include <QSslSocket>
#include <QTimer>
#include <algorithm>
#include <atomic>
#include <array>
#include <optional>
#include <thread>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>

using namespace SeamlessHunt::Hybrid;
static QSslCertificate Leaf(const QString& path) {
    QFile f(path);
    assert(f.open(QIODevice::ReadOnly));
    QSslCertificate cert(&f,QSsl::Pem);
    assert(!cert.isNull());
    return cert;
}
static QByteArray Pin(const QString& path) {
    return QCryptographicHash::hash(Leaf(path).toDer(),
                                    QCryptographicHash::Sha256).toHex();
}
static bool ListFromActualTls(
    const NativeTlsLocalConfig& cfg,
    NativeTlsPairListV102::PairSelectors& pairs,std::size_t& count) {
    // Actual native OpenSSL mTLS LIST, not a separate Qt test client.
    return NativeTlsPairListV102::List(cfg,pairs,count);
}
struct GameState {
    NativeOfferIdentityV84 current{};
    std::atomic<bool> live{true};
};
static bool Refresh(NativeOfferIdentityV84& out,void* arg) noexcept {
    const auto& state=*static_cast<GameState*>(arg);
    if(!state.live.load())return false;
    out=state.current;
    return true;
}
static std::uint64_t Now() {
    return static_cast<std::uint64_t>(QDateTime::currentMSecsSinceEpoch());
}
static bool RealEdge(const NativeTlsLocalConfig& x,
                     const NativeTlsLocalConfig& y,
                     const QByteArray& name_x,const QByteArray& name_y,
                     quint64 epoch_x,quint64 epoch_y,
                     std::uint64_t selector,
                     NativeTeamGrantSlotsV103* persistent_owner=nullptr,
                     GameState* persistent_self=nullptr) {
    const auto ax=P2PFullIdentityIssuerV84::AccountDigest(name_x);
    const auto by=P2PFullIdentityIssuerV84::AccountDigest(name_y);
    if(!ax || !by || !selector)return false;
    GameState temporary_self{{*ax,*by,epoch_x,303,true}};
    GameState& first=persistent_self?*persistent_self:temporary_self;
    if(persistent_self) {
        first.current={*ax,*by,epoch_x,303,true};
        first.live.store(true);
    }
    GameState second{{*by,*ax,epoch_y,303,true}};
    NativeSealedGrantInboxV84 inbox_x,inbox_y;
    bool ready_x=false,ready_y=false;
    SecurePeerOfferV84 grant_x{},grant_y{};
    bool ok=NativeTlsLocalOfferClientV91::Request(
        x,inbox_x,first.current,1,Refresh,&first,Now(),
        ready_x,nullptr,selector) && !ready_x;
    const auto* px=inbox_x.PendingForNat(Now());
    ok=ok && px;
    if(px)grant_x=*px;
    if(ok) {
        ok=NativeTlsLocalOfferClientV91::Request(
            y,inbox_y,second.current,1,Refresh,&second,Now(),
            ready_y,nullptr,selector) && ready_y;
    }
    const auto* py=inbox_y.PendingForNat(Now());
    ok=ok && py;
    if(py)grant_y=*py;
    std::array<std::uint8_t,32> x_send{},y_receive{},x_game{};
    if(ok) {
        ok=grant_x.pair_binding==selector &&
           grant_y.pair_binding==selector &&
           grant_x.direction_key==grant_y.direction_key &&
           grant_x.sender_account==grant_y.recipient_account &&
           grant_y.sender_account==grant_x.recipient_account &&
           PairKeyScheduleV89::Derive(
               grant_x,true,PairKeyPurposeV89::NatProbe,Now(),x_send) &&
           PairKeyScheduleV89::Derive(
               grant_y,false,PairKeyPurposeV89::NatProbe,Now(),y_receive) &&
           PairKeyScheduleV89::Derive(
               grant_x,true,PairKeyPurposeV89::GameData,Now(),x_game) &&
           x_send==y_receive && x_send!=x_game;
    }
    if(ok && persistent_owner) {
        // The actual native mTLS client issued and verified this V102
        // grant. Its private game-state callback must outlive this call.
        // Four independent peer grants are stored under one game owner.
        ok=persistent_self &&
           persistent_owner->InstallVerified(inbox_x,selector,77,Now());
    }
    CryptoDetail::Erase(x_send);
    CryptoDetail::Erase(y_receive);
    CryptoDetail::Erase(x_game);
    CryptoDetail::Erase(grant_x.direction_key);
    CryptoDetail::Erase(grant_y.direction_key);
    inbox_x.Revoke();inbox_y.Revoke();
    std::fprintf(stderr,"V102 real mTLS edge %s -> %s: %s\n",
                 name_x.constData(),name_y.constData(),ok?"PASS":"FAIL");
    return ok;
}
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);
    // Fail closed before the network test: canonical lower-hex IDs only.
    NativeTlsPairListV102::PairSelectors parsed{};
    std::size_t parsed_count=99;
    assert(NativeTlsPairListV102::Parse(
        "YT-P2P/V102 PAIRS\n",parsed,parsed_count) &&
        parsed_count==0);
    assert(NativeTlsPairListV102::Parse(
        "YT-P2P/V102 PAIRS 0000000000000001 0000000000000002\n",
        parsed,parsed_count) && parsed_count==2 &&
        parsed[0]==1 && parsed[1]==2);
    assert(!NativeTlsPairListV102::Parse(
        "YT-P2P/V102 PAIRS 0000000000000001 0000000000000001\n",
        parsed,parsed_count) && parsed_count==0);
    assert(!NativeTlsPairListV102::Parse(
        "YT-P2P/V102 PAIRS 0000000000000000\n",parsed,parsed_count));
    assert(!NativeTlsPairListV102::Parse(
        "YT-P2P/V102 PAIRS 000000000000000A\n",parsed,parsed_count));
    assert(!NativeTlsPairListV102::Parse(
        "YT-P2P/V102 PAIRS 0000000000000001 X\n",parsed,parsed_count));
    // server cert/key, CA, then FIVE distinct cert/key pairs, all loopback.
    assert(argc==14);
    P2PTlsListener server;
    const std::array<QByteArray,5> hunter{
        "hunter-A","hunter-B","hunter-C","hunter-D","hunter-E"};
    const std::array<quint64,5> epochs{101,202,303,404,505};
    const auto index=[&](const QByteArray& account)->int {
        for(int i=0;i<5;++i)
            if(hunter[static_cast<size_t>(i)]==account)return i;
        return -1;
    };
    const auto live=[&](const QByteArray& account)->quint64 {
        const int i=index(account);
        return i<0?0:epochs[static_cast<size_t>(i)];
    };
    for(int i=0;i<5;++i) {
        const int cert=4+i*2;
        assert(server.ConfigureLocalIdentity(
            Pin(argv[cert]),hunter[static_cast<size_t>(i)],live));
    }
    const auto scoped=[&](const QByteArray& a,const QByteArray& b)
        ->std::optional<P2PLocalOfferScope> {
        const int ia=index(a),ib=index(b);
        if(ia<0 || ib<0 || ia==ib)return std::nullopt;
        const auto target_port=
            static_cast<quint16>(45000+ib+1);
        return P2PLocalOfferScope{
            a,b,epochs[static_cast<size_t>(ia)],
            epochs[static_cast<size_t>(ib)],303,
            0x7f000001u,target_port,
            0x0a000001u+static_cast<quint32>(target_port),31314};
    };
    assert(server.StartLocal(argv[1],argv[2],argv[3],0));
    assert(server.serverAddress()==QHostAddress::LocalHost);
    std::uint64_t grant[5][5]{};
    for(int i=0;i<5;++i)
        for(int j=i+1;j<5;++j) {
            assert(server.ConfigureLocalTeamPairV102(
                hunter[static_cast<size_t>(i)],
                hunter[static_cast<size_t>(j)],
                scoped,grant[i][j]));
            assert(grant[i][j]);
            for(int earlier=0;earlier<j;++earlier)
                for(int earlier_peer=earlier+1;earlier_peer<5;++earlier_peer)
                    if(earlier<i || (earlier==i && earlier_peer<j))
                        assert(grant[i][j]!=grant[earlier][earlier_peer]);
        }
    std::uint64_t invalid=1;
    assert(!server.ConfigureLocalTeamPairV102(
        "hunter-A","hunter-E",scoped,invalid));
    assert(invalid==0);
    const auto port=server.serverPort();
    std::array<NativeTlsLocalConfig,5> configs{};
    for(int i=0;i<5;++i)
        configs[static_cast<size_t>(i)]=
            NativeTlsLocalConfig{argv[3],argv[4+i*2],argv[5+i*2],port};
    std::atomic<int> exit_code{-1};
    std::thread worker;
    QTimer::singleShot(0,&app,[&] {
        worker=std::thread([&] {
            // Five REAL native TLS clients discover their 4 current
            // server-issued selectors without client-supplied peer IDs.
            std::array<NativeTlsPairListV102::PairSelectors,5> lists{};
            std::array<std::size_t,5> counts{};
            bool good=true;
            for(int i=0;i<5 && good;++i)
                good=ListFromActualTls(configs[static_cast<size_t>(i)],
                    lists[static_cast<size_t>(i)],
                    counts[static_cast<size_t>(i)]) &&
                    counts[static_cast<size_t>(i)]==4;
            for(int who=0;who<5 && good;++who)
                for(int i=0;i<5;++i)
                    for(int j=i+1;j<5;++j) {
                        const auto& pairs=lists[static_cast<size_t>(who)];
                        const auto last=pairs.begin()+counts[static_cast<size_t>(who)];
                        const bool found=std::find(
                            pairs.begin(),last,grant[i][j])!=last;
                        const bool authorized=(who==i || who==j);
                        if(found!=authorized)good=false;
                    }
            std::fprintf(stderr,"V102 actual TLS five-client scoped LIST: %s\n",
                         good?"PASS":"FAIL");
            // Five independent certificate identities, ten different
            // pair grants, one SHG2 master per edge, mutual dual READY.
            NativeTeamGrantSlotsV103 original_game_owner;
            std::array<GameState,4> persistent_game_accounts{};
            for(int i=0;i<5 && good;++i)
                for(int j=i+1;j<5 && good;++j)
                    good=RealEdge(
                        configs[static_cast<size_t>(i)],
                        configs[static_cast<size_t>(j)],
                        hunter[static_cast<size_t>(i)],
                        hunter[static_cast<size_t>(j)],
                        epochs[static_cast<size_t>(i)],
                        epochs[static_cast<size_t>(j)],
                        grant[i][j],
                        i==0?&original_game_owner:nullptr,
                        i==0?&persistent_game_accounts[
                            static_cast<size_t>(j-1)]:nullptr);
            if(good) {
                good=original_game_owner.Count()==4;
                for(int j=1;j<5 && good;++j)
                    good=original_game_owner.PendingForNat(
                        grant[0][j],77,Now())!=nullptr;
                // A live opt-out must revoke only that player's edge,
                // without destroying the other three authenticated keys.
                if(good) {
                    persistent_game_accounts[0].live.store(false);
                    good=!original_game_owner.PendingForNat(
                        grant[0][1],77,Now()) &&
                        original_game_owner.Count()==3 &&
                        original_game_owner.PendingForNat(
                            grant[0][2],77,Now())!=nullptr;
                }
                original_game_owner.RevokeAll();
                good=good && original_game_owner.Count()==0;
                std::fprintf(stderr,
                    "V103 five-hunter original native owner four independent mTLS grants: %s\n",
                    good?"PASS":"FAIL");
            }
            exit_code.store(good?0:1);
            QMetaObject::invokeMethod(&app,[&] {app.quit();},
                                      Qt::QueuedConnection);
        });
    });
    QTimer::singleShot(90000,&app,[&]{app.exit(9);});
    const int event=app.exec();
    if(worker.joinable())worker.join();
    return event==0 && exit_code.load()==0?0:1;
}
