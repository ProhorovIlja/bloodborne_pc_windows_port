// SPDX-License-Identifier: GPL-2.0-or-later
// V71: test actual Direct-first SendFrame policy, HMAC SHP1 wire encoding,
// original SHAD fallback behavior, cooldown and server epoch revocation.
#include "sh_native_direct_tx.hpp"
#include "sh_direct_crypto.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;

static void U32(std::vector<std::uint8_t>& dst,std::uint32_t n) {
    for(unsigned i=0;i<32;i+=8) dst.push_back(static_cast<std::uint8_t>(n>>i));
}
static std::vector<std::uint8_t> Game(std::uint32_t chan,char sender='A',
                                      unsigned extra=0) {
    std::vector<std::uint8_t> f{255,255,255,255,'S','H','A','D',0x40,1,1,
                                static_cast<std::uint8_t>(sender)};
    U32(f,1);U32(f,1);U32(f,0);
    f.push_back(1);f.push_back(0);
    f.push_back(static_cast<std::uint8_t>(chan>6?1:0));
    U32(f,17);U32(f,8+extra);U32(f,chan);U32(f,extra);
    f.insert(f.end(),extra,0x28);
    return f;
}
struct ServerWorld { bool active=true;ChannelAuthority policy{}; };
static bool Refresh(ChannelAuthority& a,void* ctx) noexcept {
    auto& w=*static_cast<ServerWorld*>(ctx);
    if(!w.active) return false;
    a=w.policy;return true;
}
static ChannelAuthority Allowed() {
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
        a.both_on_same_authorized_team=a.protocol_compatible=
        a.map_known=a.map_epoch_verified=a.both_on_same_map=
        a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
static PeerTicket Ticket() {
    PeerTicket t{};
    t.session_epoch=101;t.pair_binding=202;
    t.authenticated_sender=31;t.local_receiver=32;
    t.expires_at_ms=20000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static Grant Granted() {
    Grant g{};
    g.session_epoch=101;g.peer_binding=202;g.valid_until_ms=20000;
    g.verified_server_authorization=g.local_consent=
        g.peer_consent=g.protocol_compatible=true;
    return g;
}
static std::array<std::uint8_t,32> Key(){
    std::array<std::uint8_t,32> b{};
    for(unsigned i=0;i<32;i++) b[i]=static_cast<std::uint8_t>(20+i);
    return b;
}
struct Wire {
    DirectEncoder* enc=nullptr;
    bool force_error=false;
    std::uint64_t total=0;
    PhysicalV4 last_target{};
    std::vector<std::uint8_t> last{};
};
static bool SendAuthenticated(PhysicalV4 dest,
                              std::span<const std::uint8_t> data,
                              std::int64_t now,void* ctx) noexcept {
    auto& w=*static_cast<Wire*>(ctx);
    if(w.force_error || !w.enc) return false;
    w.last_target=dest;
    try {
        if(!w.enc->Encode(DirectKind::GameData,data,now,w.last))return false;
    } catch (...) {return false;}
    ++w.total;
    return true;
}
int main() {
    const auto t=Ticket();auto grant=Granted();auto auth=Allowed();
    const VirtualV4 dest{0x7f000001U,12345};
    const PhysicalV4 phys{0x7f000001U,54321};
    const auto frame=Game(0x06);
    NativeDirectSender tx;
    assert(tx.TrySend(dest,frame,100)==NativeTxStatus::RelayRequired);
    ServerWorld world{true,auth};
    DirectionMac mac;assert(mac.InstallKey(Key()));
    DirectEncoder enc;assert(enc.Arm(t,mac,100));
    Wire wire{&enc};
    auto bad=t;bad.server_grant_verified=false;
    assert(!tx.Arm(0,bad,grant,dest,phys,"A",Refresh,&world,SendAuthenticated,&wire,100));
    bad=t;bad.pair_binding++;
    assert(!tx.Arm(0,bad,grant,dest,phys,"A",Refresh,&world,SendAuthenticated,&wire,100));
    assert(!tx.Arm(9,t,grant,dest,phys,"A",Refresh,&world,SendAuthenticated,&wire,100));
    assert(!tx.Arm(0,t,grant,{},phys,"A",Refresh,&world,SendAuthenticated,&wire,100));
    assert(!tx.Arm(0,t,grant,dest,{},"A",Refresh,&world,SendAuthenticated,&wire,100));
    assert(!tx.Arm(0,t,grant,dest,phys,"A",nullptr,&world,SendAuthenticated,&wire,100));
    assert(!tx.Arm(0,t,grant,dest,phys,"A",Refresh,&world,nullptr,&wire,100));
    grant.peer_consent=false;
    assert(!tx.Arm(0,t,grant,dest,phys,"A",Refresh,&world,SendAuthenticated,&wire,100));
    grant=Granted();
    assert(tx.Arm(0,t,grant,dest,phys,"A",Refresh,&world,SendAuthenticated,&wire,100));
    assert(tx.TrySend({dest.addr_nbo,54321},frame,105)==NativeTxStatus::RelayRequired);
    assert(tx.TrySend(dest,frame,106)==NativeTxStatus::DirectSubmitted);
    assert(wire.total==1 && wire.last_target.addr_nbo==phys.addr_nbo);
    DirectReceiver receiver;assert(receiver.Arm(t,100));
    DirectFrame accepted{};
    assert(receiver.Receive(wire.last,106,DirectionMac::VerifyCallback,&mac,accepted));
    assert(accepted.kind==DirectKind::GameData);
    assert(std::equal(accepted.payload.begin(),accepted.payload.end(),frame.begin()));
    assert(!receiver.Receive(wire.last,106,DirectionMac::VerifyCallback,&mac,accepted));
    assert(tx.TrySend(dest,Game(0x2f),107)==NativeTxStatus::RelayRequired);
    assert(tx.TrySend(dest,Game(0x06,'B'),108)==NativeTxStatus::RelayRequired);
    world.policy.map_epoch_verified=false;
    assert(tx.TrySend(dest,frame,109)==NativeTxStatus::RelayRequired);
    world.policy=auth;
    auto too_big=Game(0x06,'A',DirectReceiver::kMaxPayloadBytes);
    assert(tx.TrySend(dest,too_big,110)==NativeTxStatus::RelayRequired);
    assert(wire.total==1);
    assert(tx.TrySend(dest,frame,111)==NativeTxStatus::DirectSubmitted);
    wire.force_error=true;
    assert(tx.TrySend(dest,frame,112)==NativeTxStatus::RelayRequired);
    wire.force_error=false;
    assert(tx.TrySend(dest,frame,113)==NativeTxStatus::RelayRequired);
    assert(wire.total==2); // original relay owns BOTH unsuccessful submissions
    assert(tx.TrySend(dest,frame,10112)==NativeTxStatus::DirectSubmitted);
    assert(wire.total==3);
    world.active=false;
    assert(tx.TrySend(dest,frame,10113)==NativeTxStatus::RelayRequired);
    world.active=true;
    assert(tx.TrySend(dest,frame,10114)==NativeTxStatus::RelayRequired);
    assert(tx.Arm(0,t,grant,dest,phys,"A",Refresh,&world,SendAuthenticated,&wire,15000));
    assert(tx.TrySend(dest,frame,20000)==NativeTxStatus::RelayRequired);
    assert(tx.TrySend(dest,frame,20001)==NativeTxStatus::RelayRequired);
    tx.RevokeAll();
    assert(tx.TrySend(dest,frame,19000)==NativeTxStatus::RelayRequired);
    return 0;
}
