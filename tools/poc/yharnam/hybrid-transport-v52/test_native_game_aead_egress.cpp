// SPDX-License-Identifier: GPL-2.0-or-later
// SHY2 encrypted outgoing real-native-frame eligibility and reciprocal
// decrypted incoming proof. No session is installed by the game yet.
#include "sh_native_game_aead_egress.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;
struct World{bool enabled=true;ChannelAuthority auth{};};
static bool Refresh(ChannelAuthority& out,void* ctx) noexcept {
    auto& w=*static_cast<World*>(ctx);if(!w.enabled)return false;
    out=w.auth;return true;
}
static ChannelAuthority Allowed(){
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
      a.both_on_same_authorized_team=a.protocol_compatible=
      a.map_known=a.map_epoch_verified=a.both_on_same_map=
      a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;return a;
}
static PeerTicket Ticket(std::uint64_t pair,std::uint64_t sender=10) {
    PeerTicket t{};
    t.session_epoch=77;t.pair_binding=pair;
    t.authenticated_sender=sender;t.local_receiver=88;
    t.expires_at_ms=2000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static std::array<std::uint8_t,32> Key(unsigned seed){
    std::array<std::uint8_t,32> k{};
    for(unsigned i=0;i<k.size();++i)
        k[i]=static_cast<std::uint8_t>(seed+i);
    return k;
}
static std::array<std::uint8_t,4> Salt(unsigned seed){
    return {static_cast<std::uint8_t>(seed),
            static_cast<std::uint8_t>(seed+1),
            static_cast<std::uint8_t>(seed+2),
            static_cast<std::uint8_t>(seed+3)};
}
static void U32(std::vector<std::uint8_t>& x,std::uint32_t n){
    for(unsigned i=0;i<32;i+=8)x.push_back(static_cast<std::uint8_t>(n>>i));
}
static std::vector<std::uint8_t> Game(char sender,std::uint32_t ch=0x06,
                                       bool reliable=false,bool ack=false){
    std::vector<std::uint8_t> b{255,255,255,255,'S','H','A','D',0x40,1,1,
                                static_cast<std::uint8_t>(sender)};
    U32(b,1);U32(b,1);U32(b,ack?1:0);
    b.push_back(1);b.push_back(0);
    b.push_back(reliable?1:0);U32(b,17);U32(b,8);U32(b,ch);U32(b,0);
    return b;
}
int main() {
    NativeGameAeadEgress tx;
    NativeGameAeadIngress rx;
    const PhysicalV4 addr{0x0100007fU,0xa01bU};
    const VirtualV4 peer{0x0a000001U,0xe102U};
    const auto ticket=Ticket(554),key=Key(17),salt=Salt(83);
    World w{};w.auth=Allowed();
    const auto game=Game('A');
    std::vector<std::uint8_t> wire;
    assert(!tx.Seal(addr,game,101,wire) && wire.empty());
    assert(!tx.Arm(6,ticket,key,salt,addr,peer,"A",Refresh,&w,100));
    assert(!tx.Arm(0,ticket,key,salt,{},peer,"A",Refresh,&w,100));
    auto fake=ticket;fake.both_consented=false;
    assert(!tx.Arm(0,fake,key,salt,addr,peer,"A",Refresh,&w,100));
    assert(tx.Arm(0,ticket,key,salt,addr,peer,"A",Refresh,&w,100));
    assert(rx.Arm(0,ticket,key,salt,addr,peer,"A",Refresh,&w,100));
    assert(!tx.Arm(0,ticket,key,salt,addr,peer,"A",Refresh,&w,100));
    assert(!tx.Arm(1,Ticket(555,11),Key(18),Salt(84),addr,
                   VirtualV4{9,9},"B",Refresh,&w,100));
    assert(!tx.Seal(PhysicalV4{1,2},game,102,wire));
    assert(!tx.Seal(addr,Game('B'),102,wire));
    assert(!tx.Seal(addr,Game('A',0x2f),102,wire));
    assert(!tx.Seal(addr,Game('A',0x14,true),102,wire));
    assert(!tx.Seal(addr,Game('A',0x06,false,true),102,wire));
    assert(tx.Seal(addr,game,103,wire));
    assert(wire.size()>game.size());
    auto received=rx.Receive(addr,wire,103);
    assert(received.status==NativeRxStatus::Game);
    assert(received.native_game_frame==game);
    assert(rx.Receive(addr,wire,104).status==NativeRxStatus::Dropped);
    w.auth.map_epoch_verified=false;
    assert(!tx.Seal(addr,game,105,wire) && wire.empty());
    w.auth.map_epoch_verified=true;
    assert(tx.Seal(addr,game,106,wire));
    assert(rx.Receive(addr,wire,106).status==NativeRxStatus::Game);
    w.enabled=false;
    assert(!tx.Seal(addr,game,107,wire));
    w.enabled=true;
    assert(!tx.Seal(addr,game,108,wire));
    assert(!tx.Arm(0,ticket,key,salt,addr,peer,"A",Refresh,&w,109));
    // Independent 5-person team only authorizes four remote peers;
    // unique per-pair nonce spaces, endpoints, and virtual game senders.
    for(unsigned i=1;i<=3;++i) {
        const PhysicalV4 ip{0x0100007fU,static_cast<std::uint16_t>(0xa01b+i)};
        const VirtualV4 vp{0x0a000001U,static_cast<std::uint16_t>(0xe102+i)};
        const auto t=Ticket(554+i,10+i);
        assert(tx.Arm(i,t,Key(30+i),Salt(100+i),
                      ip,vp,"B",Refresh,&w,110));
        assert(rx.Arm(i,t,Key(30+i),Salt(100+i),
                      ip,vp,"B",Refresh,&w,110));
        assert(tx.Seal(ip,Game('B'),111,wire));
        assert(rx.Receive(ip,wire,111).status==NativeRxStatus::Game);
    }
    tx.RevokeAll();rx.RevokeAll();
    assert(!tx.Seal(addr,game,112,wire));
    assert(rx.Receive(addr,wire,112).status==NativeRxStatus::Dropped);
    return 0;
}
