// SPDX-License-Identifier: GPL-2.0-or-later
// Actual compiled SHY2 cryptographic -> authorized original-game receive
// path, with four independent pending peers. No public Direct Arm exists.
#include "sh_native_game_aead_ingress.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string_view>
#include <vector>

using namespace SeamlessHunt::Hybrid;
struct LiveWorld {bool allow=true;ChannelAuthority authority{};};
static bool Refresh(ChannelAuthority& out,void* ctx) noexcept {
    auto& live=*static_cast<LiveWorld*>(ctx);
    if(!live.allow)return false;
    out=live.authority;
    return true;
}
static ChannelAuthority Good() {
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
      a.both_on_same_authorized_team=a.protocol_compatible=
      a.map_known=a.map_epoch_verified=a.both_on_same_map=
      a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
static std::array<std::uint8_t,32> Key(unsigned seed) {
    std::array<std::uint8_t,32> k{};
    for(unsigned i=0;i<k.size();++i)
        k[i]=static_cast<std::uint8_t>(seed+i);
    return k;
}
static std::array<std::uint8_t,4> Salt(unsigned seed) {
    return {static_cast<std::uint8_t>(seed),
            static_cast<std::uint8_t>(seed+1),
            static_cast<std::uint8_t>(seed+2),
            static_cast<std::uint8_t>(seed+3)};
}
static void U32(std::vector<std::uint8_t>& b,std::uint32_t v) {
    for(unsigned shift=0;shift<32;shift+=8)
        b.push_back(static_cast<std::uint8_t>(v>>shift));
}
static std::vector<std::uint8_t> Frame(std::string_view sender,
                                        std::uint32_t channel=0x06,
                                        bool reliable=false,bool has_ack=false) {
    assert(sender.size()==1);
    std::vector<std::uint8_t> b{255,255,255,255,'S','H','A','D',
                                0x40,1,1,static_cast<std::uint8_t>(sender[0])};
    U32(b,1);U32(b,1);U32(b,has_ack?1:0);
    b.push_back(1);b.push_back(0);
    b.push_back(reliable?1:0);
    U32(b,17);U32(b,8);U32(b,channel);U32(b,0);
    return b;
}
static PeerTicket Ticket(std::uint64_t pair,std::uint64_t sender=10) {
    PeerTicket t{};
    t.session_epoch=42;t.pair_binding=pair;
    t.authenticated_sender=sender;t.local_receiver=19;
    t.expires_at_ms=2000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
int main() {
    NativeGameAeadIngress rx;
    const PhysicalV4 physical{0x0100007fU,0x2153U};
    const VirtualV4 virtual_peer{0x09090909U,0x7711U};
    LiveWorld world{};world.authority=Good();
    auto key=Key(10),salt=Salt(71);
    NativeGameAeadSealer tx;
    auto ticket=Ticket(502);
    assert(tx.Arm(ticket,key,salt,100));
    auto game=Frame("A");
    std::vector<std::uint8_t> wire;
    assert(tx.SealGame(game,101,wire));
    assert(rx.Receive(physical,wire,101).status==NativeRxStatus::Dropped);
    const std::array<std::uint8_t,4> shlk{'S','H','L','K'};
    assert(rx.Receive(physical,shlk,101).status==NativeRxStatus::NotDirect);
    assert(!rx.Arm(9,ticket,key,salt,physical,virtual_peer,"A",Refresh,&world,100));
    assert(!rx.Arm(0,ticket,key,salt,{},virtual_peer,"A",Refresh,&world,100));
    assert(!rx.Arm(0,ticket,key,salt,physical,{},"A",Refresh,&world,100));
    auto unapproved=ticket;unapproved.server_grant_verified=false;
    assert(!rx.Arm(0,unapproved,key,salt,physical,virtual_peer,"A",Refresh,&world,100));
    assert(rx.Arm(0,ticket,key,salt,physical,virtual_peer,"A",Refresh,&world,100));
    assert(!rx.Arm(0,ticket,key,salt,physical,virtual_peer,"A",Refresh,&world,100));
    assert(!rx.Arm(1,Ticket(503,11),Key(21),Salt(81),
                   physical,VirtualV4{1,2},"B",Refresh,&world,100));
    assert(!rx.Arm(1,ticket,key,salt,PhysicalV4{3,4},
                   VirtualV4{5,6},"A",Refresh,&world,100));
    assert(rx.Receive(PhysicalV4{physical.addr_nbo,0x9999},wire,101).status==
           NativeRxStatus::Dropped);
    auto bad=wire;bad.back()^=1;
    assert(rx.Receive(physical,bad,102).status==NativeRxStatus::Dropped);
    auto good=rx.Receive(physical,wire,102);
    assert(good.status==NativeRxStatus::Game && good.native_game_frame==game);
    assert(good.sender.addr_nbo==virtual_peer.addr_nbo &&
           good.sender.port_nbo==virtual_peer.port_nbo);
    assert(rx.Receive(physical,wire,103).status==NativeRxStatus::Dropped);
    assert(tx.SealGame(Frame("B"),104,wire));
    assert(rx.Receive(physical,wire,104).status==NativeRxStatus::Dropped);
    assert(tx.SealGame(Frame("A",0x2f),105,wire)); // server-only
    assert(rx.Receive(physical,wire,105).status==NativeRxStatus::Dropped);
    assert(tx.SealGame(Frame("A",0x14,true),106,wire)); // reliable
    assert(rx.Receive(physical,wire,106).status==NativeRxStatus::Dropped);
    assert(tx.SealGame(Frame("A",0x06,false,true),107,wire)); // shared ACK
    assert(rx.Receive(physical,wire,107).status==NativeRxStatus::Dropped);
    world.authority.map_epoch_verified=false;
    assert(tx.SealGame(game,108,wire));
    assert(rx.Receive(physical,wire,108).status==NativeRxStatus::Dropped);
    world.authority.map_epoch_verified=true;
    assert(tx.SealGame(game,109,wire));
    assert(rx.Receive(physical,wire,109).status==NativeRxStatus::Game);
    // A former server-granted remote loses consent; cannot be revived by
    // simply toggling a client-local boolean back to true.
    world.allow=false;
    assert(tx.SealGame(game,110,wire));
    assert(rx.Receive(physical,wire,110).status==NativeRxStatus::Dropped);
    world.allow=true;
    assert(rx.Receive(physical,wire,111).status==NativeRxStatus::Dropped);
    assert(!rx.Arm(0,ticket,key,salt,physical,virtual_peer,"A",Refresh,&world,112));
    // Independent peers have their OWN replay and physical/virtual mapping.
    for(unsigned i=1;i<=3;++i) {
        const auto other=Ticket(502+i,10+i);
        const auto pp=PhysicalV4{0x0100007fU,static_cast<std::uint16_t>(0x2153+i)};
        const auto vv=VirtualV4{0x09090909U,static_cast<std::uint16_t>(0x7711+i)};
        assert(rx.Arm(i,other,Key(20+i),Salt(90+i),pp,vv,
                      "B",Refresh,&world,120));
        NativeGameAeadSealer tx_other;
        assert(tx_other.Arm(other,Key(20+i),Salt(90+i),120));
        assert(tx_other.SealGame(Frame("B"),121,wire));
        assert(rx.Receive(pp,wire,121).status==NativeRxStatus::Game);
    }
    rx.RevokeAll();
    assert(rx.Receive(physical,wire,122).status==NativeRxStatus::Dropped);
    return 0;
}
