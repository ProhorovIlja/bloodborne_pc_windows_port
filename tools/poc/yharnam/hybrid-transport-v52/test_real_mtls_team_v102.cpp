// SPDX-License-Identifier: GPL-2.0-or-later
// V102: THREE distinct native hunters, original Qt TLS1.3 server event loop,
// three real cert-pinned SHG2 exchanges A-B, A-C, B-C. Direct game OFF.
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
static std::string HexId(std::uint64_t id) {
    char hex[16]{};
    constexpr char lut[]="0123456789abcdef";
    for(unsigned i=0;i<16;++i)
        hex[15U-i]=lut[(id>>(4U*i))&0x0fU];
    return std::string(hex,sizeof(hex));
}
static bool ListFromActualTls(const QString& ca,const QString& cert,
                              const QString& key,quint16 port,
                              QByteArray& response) {
    response.clear();
    QFile f(key);
    if(!f.open(QIODevice::ReadOnly))return false;
    const QSslKey private_key(&f,QSsl::Rsa,QSsl::Pem,QSsl::PrivateKey);
    if(private_key.isNull())return false;
    QSslConfiguration cfg=QSslConfiguration::defaultConfiguration();
    cfg.setProtocol(QSsl::TlsV1_3);
    cfg.setCaCertificates({Leaf(ca)});
    cfg.setLocalCertificate(Leaf(cert));
    cfg.setPrivateKey(private_key);
    cfg.setPeerVerifyMode(QSslSocket::VerifyPeer);
    QSslSocket s;
    s.setSslConfiguration(cfg);
    s.connectToHostEncrypted("127.0.0.1",port);
    if(!s.waitForEncrypted(3000))return false;
    constexpr char cmd[]="YT-P2P/V102 LIST\n";
    if(s.write(cmd,sizeof(cmd)-1)!=sizeof(cmd)-1 ||
       !s.waitForBytesWritten(3000))return false;
    for(int i=0;i<4 && !response.contains('\n');++i) {
        if(!s.waitForReadyRead(1500))break;
        response+=s.readAll();
    }
    if(response.contains('\n')) {
        response=response.left(response.indexOf('\n')+1);
        return response.startsWith("YT-P2P/V102 PAIRS") &&
               response.endsWith('\n');
    }
    return false;
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
                     std::uint64_t selector) {
    const auto ax=P2PFullIdentityIssuerV84::AccountDigest(name_x);
    const auto by=P2PFullIdentityIssuerV84::AccountDigest(name_y);
    if(!ax || !by || !selector)return false;
    GameState first{{*ax,*by,epoch_x,303,true}};
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
    // server.pem server.key ca.pem a.pem a.key b.pem b.key c.pem c.key
    assert(argc==10);
    P2PTlsListener server;
    const auto live=[](const QByteArray& name)->quint64 {
        if(name=="hunter-A")return 101;
        if(name=="hunter-B")return 202;
        if(name=="hunter-C")return 303;
        return 0;
    };
    assert(server.ConfigureLocalIdentity(Pin(argv[4]),"hunter-A",live));
    assert(server.ConfigureLocalIdentity(Pin(argv[6]),"hunter-B",live));
    assert(server.ConfigureLocalIdentity(Pin(argv[8]),"hunter-C",live));
    auto scoped=[](const QByteArray& a,const QByteArray& b)
        ->std::optional<P2PLocalOfferScope> {
        const auto epoch=[](const QByteArray& who)->quint64 {
            if(who=="hunter-A")return 101;
            if(who=="hunter-B")return 202;
            if(who=="hunter-C")return 303;
            return 0;
        };
        const auto port=[](const QByteArray& who)->quint16 {
            if(who=="hunter-A")return 45101;
            if(who=="hunter-B")return 45202;
            if(who=="hunter-C")return 45303;
            return 0;
        };
        if(a==b || !epoch(a) || !epoch(b))return std::nullopt;
        return P2PLocalOfferScope{a,b,epoch(a),epoch(b),303,
            0x7f000001u,port(b),
            0x0a000001u+static_cast<quint32>(port(b)),31314};
    };
    assert(server.StartLocal(argv[1],argv[2],argv[3],0));
    assert(server.serverAddress()==QHostAddress::LocalHost);
    std::uint64_t ab=0,ac=0,bc=0,invalid=0;
    assert(server.ConfigureLocalTeamPairV102(
        "hunter-A","hunter-B",scoped,ab));
    assert(server.ConfigureLocalTeamPairV102(
        "hunter-A","hunter-C",scoped,ac));
    assert(server.ConfigureLocalTeamPairV102(
        "hunter-B","hunter-C",scoped,bc));
    assert(ab && ac && bc && ab!=ac && ab!=bc && ac!=bc);
    assert(!server.ConfigureLocalTeamPairV102(
        "hunter-B","hunter-A",scoped,invalid));
    assert(invalid==0);
    const quint16 port=server.serverPort();
    NativeTlsLocalConfig cfg_a{argv[3],argv[4],argv[5],port};
    NativeTlsLocalConfig cfg_b{argv[3],argv[6],argv[7],port};
    NativeTlsLocalConfig cfg_c{argv[3],argv[8],argv[9],port};
    std::atomic<int> exit_code{-1};
    std::thread worker;
    QTimer::singleShot(0,&app,[&] {
        worker=std::thread([&] {
            QByteArray a_list,b_list,c_list;
            bool good=ListFromActualTls(
                argv[3],argv[4],argv[5],port,a_list) &&
                ListFromActualTls(
                argv[3],argv[6],argv[7],port,b_list) &&
                ListFromActualTls(
                argv[3],argv[8],argv[9],port,c_list);
            const auto ab_hex=QByteArray::fromStdString(HexId(ab));
            const auto ac_hex=QByteArray::fromStdString(HexId(ac));
            const auto bc_hex=QByteArray::fromStdString(HexId(bc));
            good=good &&
                 a_list.contains(ab_hex) && a_list.contains(ac_hex) &&
                 !a_list.contains(bc_hex) &&
                 b_list.contains(ab_hex) && b_list.contains(bc_hex) &&
                 !b_list.contains(ac_hex) &&
                 c_list.contains(ac_hex) && c_list.contains(bc_hex) &&
                 !c_list.contains(ab_hex);
            std::fprintf(stderr,"V102 actual TLS scoped 3-player LIST: %s\n",
                         good?"PASS":"FAIL");
            // Three independent full native TLS BEGIN/OFFER/READY pairs,
            // with A and B legitimately taking two peer-specific tickets.
            if(good)good=RealEdge(
                cfg_a,cfg_b,"hunter-A","hunter-B",101,202,ab);
            if(good)good=RealEdge(
                cfg_a,cfg_c,"hunter-A","hunter-C",101,303,ac);
            if(good)good=RealEdge(
                cfg_b,cfg_c,"hunter-B","hunter-C",202,303,bc);
            exit_code.store(good?0:1);
            QMetaObject::invokeMethod(&app,[&] {
                app.quit();
            },Qt::QueuedConnection);
        });
    });
    QTimer::singleShot(30000,&app,[&]{app.exit(9);});
    const int event=app.exec();
    if(worker.joinable())worker.join();
    return event==0 && exit_code.load()==0?0:1;
}
