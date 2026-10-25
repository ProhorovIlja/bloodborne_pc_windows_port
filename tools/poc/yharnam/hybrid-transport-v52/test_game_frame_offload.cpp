// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_game_frame_offload.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static void U16(std::vector<std::uint8_t>& b, std::uint16_t n) {
    b.push_back(n&255);
    b.push_back((n>>8)&255);
}
static void U32(std::vector<std::uint8_t>& b, std::uint32_t n) {
    for(int i=0; i<32; i+=8) b.push_back((n>>i)&255);
}
static std::vector<std::uint8_t> Frame(std::uint32_t channel, bool reliable, bool ack_only=false) {
    std::vector<std::uint8_t> b{0xff,0xff,0xff,0xff,'S','H','A','D',0x40,1,1,'X'};
    U32(b,1);U32(b,1);U32(b,0);
    U16(b,ack_only?0:1);
    if(!ack_only) {
        b.push_back(reliable?1:0); U32(b,11); U32(b,8);
        U32(b,channel); U32(b,0);
    }
    return b;
}
static ChannelAuthority Good() {
    ChannelAuthority a{};
    a.session_grant_verified = true;
    a.both_peers_consented = true;
    a.peer_binding_verified = true;
    a.both_on_same_authorized_team = true;
    a.protocol_compatible = true;
    a.map_known = a.map_epoch_verified = a.both_on_same_map = true;
    a.enemy_stream_authorized = true;
    a.reliable_stream_handover_verified = true;
    a.sender_enemy_role = EnemyRole::Owner;
    a.target_enemy_role = EnemyRole::Follower;
    return a;
}
static bool Valid(const std::vector<std::uint8_t>& b, const ChannelAuthority& a,
                  std::string_view peer="X",
                  bool real_reliable_handover=true) {
    return EligibleNativeWireFrame(b, peer, a, real_reliable_handover).direct_eligible;
}
int main() {
    auto a=Good();
    assert(Valid(Frame(0x06,false),a));
    assert(Valid(Frame(0x06,false),a,"X",false)); // candidate Direct movement
    assert(!Valid(Frame(0x14,true),a,"X",false)); // reliable is still relay
    assert(!Valid(Frame(0,true,true),a,"X",false)); // ACK-only is relay
    {
        auto has_ack=Frame(0x06,false);
        has_ack[20]=1; // native GameLink shared ACK header is nonzero
        assert(Valid(has_ack,a,"X",true)); // hypothetical full stream migration
        assert(!Valid(has_ack,a,"X",false)); // real native runtime MUST relay
    }
    {
        auto mixed=Frame(0x06,false);
        auto second=Frame(0x14,true);
        mixed[24]=2; // two entries
        mixed.insert(mixed.end(),second.begin()+26,second.end());
        assert(Valid(mixed,a,"X",true));
        assert(!Valid(mixed,a,"X",false)); // entire mixed frame relays
    }
    assert(Valid(Frame(0x04,false),a));
    assert(Valid(Frame(0x14,true),a));
    assert(Valid(Frame(0x05,false),a));
    assert(Valid(Frame(0x40,true),a));
    assert(Valid(Frame(0x01,false),a));
    assert(Valid(Frame(0x06,false),a)==true);
    assert(!Valid(Frame(0x2C,true),a)); // item: server authority
    assert(!Valid(Frame(0x27,true),a)); // drop, never peer
    assert(!Valid(Frame(0x2F,true),a)); // world corrections
    assert(!Valid(Frame(0x06,true),a)); // forged reliability class
    assert(!Valid(Frame(0x14,false),a));
    assert(Valid(Frame(0,true,true),a)); // verified ACK-only
    auto noReliable=Good();
    noReliable.reliable_stream_handover_verified=false;
    assert(Valid(Frame(0x06,false),noReliable));
    assert(!Valid(Frame(0x14,true),noReliable));
    assert(!Valid(Frame(0,true,true),noReliable));
    auto otherMap=Good();
    otherMap.both_on_same_map=false;
    assert(!Valid(Frame(0x06,false),otherMap));
    assert(Valid(Frame(0x01,false),otherMap));
    auto noConsent=Good();
    noConsent.both_peers_consented=false;
    assert(!Valid(Frame(0x06,false),noConsent));
    assert(!Valid(Frame(0x14,true),noConsent));
    auto enemyGone=Good();
    enemyGone.enemy_stream_authorized=false;
    assert(!Valid(Frame(0x04,false),enemyGone));
    assert(Valid(Frame(0x06,false),enemyGone));
    assert(!Valid(Frame(0x06,false),a,"Y"));
    for (int offset : {4,5,6,7,8,9}) {
        auto bad=Frame(0x06,false);
        bad[static_cast<std::size_t>(offset)]=0;
        assert(!Valid(bad,a));
    }
    {
        auto bad=Frame(0x14,true);bad.pop_back();
        assert(!Valid(bad,a)); // truncated native packet
    }
    {
        auto bad=Frame(0x14,true);bad[bad.size()-8]=0x00;bad[bad.size()-7]=0x60;
        assert(!Valid(bad,a)); // out of range channel
    }
    {
        auto bad=Frame(0x06,false);
        bad.back()=1; // claimed 1 payload byte, actual 0
        assert(!Valid(bad,a));
    }
    {
        auto bad=Frame(0x06,false);bad.push_back(0);
        assert(!Valid(bad,a)); // trailing junk
    }
    {
        auto bad=Frame(0x06,false);bad[24]=81;
        assert(!Valid(bad,a)); // illegal >80 entries
    }
    {
        auto bad=Frame(0x06,false);bad[26]=2;
        assert(!Valid(bad,a)); // unsupported game packet class
    }
    return 0;
}
