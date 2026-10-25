// SPDX-License-Identifier: GPL-2.0-or-later
// V70: same-game-socket incoming SHP1 demux, real CNG/OpenSSL HMAC,
// current world permission, virtual peer mapping and default-deny.
#include "sh_native_direct_rx.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <string_view>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static void U32(std::vector<std::uint8_t>& dst,std::uint32_t v) {
    for(unsigned i=0;i<32;i+=8) dst.push_back(static_cast<std::uint8_t>(v>>i));
}
static std::vector<std::uint8_t> NativeGame(std::uint32_t channel,
                                            std::string_view sender) {
    assert(sender.size()==1);
    std::vector<std::uint8_t> frame{255,255,255,255,'S','H','A','D',0x40,1,1,
                                    static_cast<std::uint8_t>(sender[0])};
    U32(frame,1);U32(frame,1);U32(frame,0);
    frame.push_back(1);frame.push_back(0);
    frame.push_back(static_cast<std::uint8_t>(channel>6?1:0));
    U32(frame,17);U32(frame,8);U32(frame,channel);U32(frame,0);
    return frame;
}
static PeerTicket Ticket() {
    PeerTicket t{};t.session_epoch=87;t.pair_binding=765;
    t.authenticated_sender=21;t.local_receiver=22;t.expires_at_ms=20000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static Grant ServerGrant() {
    Grant g{};g.session_epoch=87;g.peer_binding=765;g.valid_until_ms=20000;
    g.verified_server_authorization=g.local_consent=
        g.peer_consent=g.protocol_compatible=true;
    return g;
}
struct Current {
    bool allowed=true;
    ChannelAuthority authority{};
};
static bool Refresh(ChannelAuthority& a,void* ctx) noexcept {
    auto& state=*static_cast<Current*>(ctx);
    if(!state.allowed) return false;
    a=state.authority;
    return true;
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
static std::array<std::uint8_t,32> Key(){
    std::array<std::uint8_t,32> k{};
    for(unsigned i=0;i<32;++i)k[i]=static_cast<std::uint8_t>(i+1);
    return k;
}
static NativeRxStatus Send(DirectEncoder& encoder,NativeDirectReceiver& recv,
                            DirectKind kind,
                            std::span<const std::uint8_t> payload,
                            PhysicalV4 physical,std::int64_t now,
                            NativeRxResult* result=nullptr){
    std::vector<std::uint8_t> wire;
    assert(encoder.Encode(kind,payload,now,wire));
    auto out=recv.Receive(physical,wire,now);
    if(out.status==NativeRxStatus::Game) {
        assert(out.native_game_frame.size()==payload.size());
        assert(std::equal(out.native_game_frame.begin(),out.native_game_frame.end(),payload.begin()));
    }
    if(result) { result->status=out.status;result->sender=out.sender; } // no dangling span
    return out.status;
}
int main(){
    const auto ticket=Ticket();
    const auto grant=ServerGrant();
    const auto physical=PhysicalV4{0x0100007fU,0xa6b5U};
    const auto virtual_peer=VirtualV4{0x0a000010U,0x7530U};
    Current world{};world.authority=Allowed();
    NativeDirectReceiver r;
    DirectionMac sender;
    assert(sender.InstallKey(Key()));
    DirectEncoder encoder;
    assert(encoder.Arm(ticket,sender,100));
    auto wire=NativeGame(0x06,"A");
    // Before a trusted server control installer exists: all SHP1 is DROP,
    // not sent to legacy SHLK or game sockets.
    std::vector<std::uint8_t> frame;
    assert(encoder.Encode(DirectKind::GameData,wire,101,frame));
    assert(r.Receive(physical,frame,101).status==NativeRxStatus::Dropped);
    const std::array<std::uint8_t,4> shlk{'S','H','L','K'};
    assert(r.Receive(physical,shlk,101).status==NativeRxStatus::NotDirect);
    assert(r.Receive(physical,std::span<const std::uint8_t>{},101).status
           ==NativeRxStatus::NotDirect);
    assert(!r.Arm(999,ticket,grant,Key(),physical,virtual_peer,"A",Refresh,&world,100));
    auto badticket=ticket; badticket.server_grant_verified=false;
    assert(!r.Arm(0,badticket,grant,Key(),physical,virtual_peer,"A",Refresh,&world,100));
    assert(!r.Arm(0,ticket,grant,Key(),{},virtual_peer,"A",Refresh,&world,100));
    assert(!r.Arm(0,ticket,grant,Key(),physical,{},"A",Refresh,&world,100));
    assert(!r.Arm(0,ticket,grant,Key(),physical,virtual_peer,"A",nullptr,&world,100));
    const std::array<std::uint8_t,32> zero{};
    assert(!r.Arm(0,ticket,grant,zero,physical,virtual_peer,"A",Refresh,&world,100));
    assert(r.Arm(0,ticket,grant,Key(),physical,virtual_peer,"A",Refresh,&world,100));
    // Bad MAC must not corrupt replay window: next correct seq packet works.
    DirectionMac impostor;auto altered=Key();altered[5]^=7;
    assert(impostor.InstallKey(altered));
    DirectEncoder bad;assert(bad.Arm(ticket,impostor,100));
    assert(Send(bad,r,DirectKind::Probe,{},physical,102)==NativeRxStatus::Dropped);
    assert(Send(encoder,r,DirectKind::Probe,{},physical,102)==NativeRxStatus::Control);
    assert(Send(encoder,r,DirectKind::Probe,{},physical,103)==NativeRxStatus::Control);
    assert(Send(encoder,r,DirectKind::Probe,{},physical,104)==NativeRxStatus::Control);
    assert(Send(encoder,r,DirectKind::GameData,wire,
                PhysicalV4{physical.addr_nbo,0xb64aU},105)==NativeRxStatus::Dropped);
    NativeRxResult game{};
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,105,&game)
           ==NativeRxStatus::Game);
    assert(game.sender.addr_nbo==virtual_peer.addr_nbo &&
           game.sender.port_nbo==virtual_peer.port_nbo);
    // No dependency on physical IP for visible in-game virtual identity.
    auto authority=world.authority;world.authority.map_epoch_verified=false;
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,106)==NativeRxStatus::Dropped);
    world.authority=authority;
    const auto authority_only=NativeGame(0x2f,"A");
    assert(Send(encoder,r,DirectKind::GameData,authority_only,physical,107)
           ==NativeRxStatus::Dropped);
    const auto wrong_sender=NativeGame(0x06,"B");
    assert(Send(encoder,r,DirectKind::GameData,wrong_sender,physical,108)
           ==NativeRxStatus::Dropped);
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,109)
           ==NativeRxStatus::Game);
    // Real-time world revocation tears down MAC/replay state; reverting
    // the world state cannot revive an obsolete pair ticket.
    world.allowed=false;
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,110)
           ==NativeRxStatus::Dropped);
    world.allowed=true;
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,111)
           ==NativeRxStatus::Dropped);
    // Even a current HMAC tag for a never-granted physical peer gets dropped.
    assert(r.Arm(0,ticket,grant,Key(),physical,virtual_peer,"A",Refresh,&world,112));
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,113)
           ==NativeRxStatus::Dropped); // new probe needed before game
    r.RevokeAll();
    assert(Send(encoder,r,DirectKind::GameData,wire,physical,114)
           ==NativeRxStatus::Dropped);
    // Bounded wire envelope size and impossible malformed source are dropped.
    std::vector<std::uint8_t> oversized(DirectReceiver::kMaxDatagramBytes+1,0);
    oversized[0]='S';oversized[1]='H';oversized[2]='P';oversized[3]='1';
    assert(r.Receive(physical,oversized,115).status==NativeRxStatus::Dropped);
    return 0;
}
