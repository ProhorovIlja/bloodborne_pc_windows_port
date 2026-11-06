// SPDX-License-Identifier: GPL-2.0-or-later
#include "shyt_yt_world_projection_v426.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
using Stage=SeamlessHunt::YtWorldStagingV425;
using Project=SeamlessHunt::YtWorldProjectionV426;
using Bytes=std::vector<std::uint8_t>;
static void V(Bytes& b,std::uint64_t n) {
    while(n>=128u){b.push_back(static_cast<std::uint8_t>(n|128u));n>>=7u;}
    b.push_back(static_cast<std::uint8_t>(n));
}
static void N(Bytes& b,unsigned field,std::uint64_t value) {
    V(b,static_cast<std::uint64_t>(field)*8u);V(b,value);
}
static void B(Bytes& b,unsigned field,const Bytes& payload) {
    V(b,static_cast<std::uint64_t>(field)*8u+2u);V(b,payload.size());
    b.insert(b.end(),payload.begin(),payload.end());
}
static Bytes E(std::uint64_t seq,std::uint32_t kind,std::uint32_t map=1u,
               std::uint32_t subject=55u,std::uint32_t value=1u) {
    Bytes e;N(e,1u,seq);N(e,2u,map);N(e,3u,kind);
    N(e,4u,subject);N(e,5u,value);return e;
}
static Bytes Snap() {
    Bytes body,wire,kills,packed,shown,hp,enemy,flag;
    N(body,1u,77u);N(body,2u,9u);
    N(kills,1u,1u);
    V(packed,55u);V(packed,300u);
    B(kills,2u,packed);B(body,3u,kills);
    N(body,4u,1u);
    N(shown,1u,55u);N(shown,2u,3u);B(body,5u,shown);
    N(body,6u,1u);B(body,7u,Bytes(1250u,0u));
    N(body,8u,23u); // ZigZag(-12)
    N(body,9u,1u);
    N(hp,1u,0x123456789ull);N(hp,2u,1u);
    N(enemy,1u,55u);N(enemy,2u,101u); // ZigZag(-51)
    N(enemy,3u,200u); // ZigZag(100)
    B(hp,3u,enemy);B(body,10u,hp);
    flag=E(9u,5u,1u,1000u,1u);
    B(body,11u,flag);N(body,12u,1u);
    B(wire,7u,body);
    return wire;
}
static Bytes Batch(std::uint64_t last,
                   const std::vector<Bytes>& events) {
    Bytes body,wire;N(body,1u,77u);N(body,2u,last);
    for(const auto& e:events)B(body,3u,e);
    B(wire,5u,body);return wire;
}
int main() {
    Stage staged;
    Project projection;
    assert(!projection.Rebuild(staged) && !projection.Ready());
    const auto snapshot=Snap();
    assert(staged.StageSnapshot(snapshot,77u,9u));
    assert(projection.Rebuild(staged));
    const auto& initial=projection.View();
    assert(initial.epoch==77u && initial.applied==9u &&
           initial.game_applied==0u && initial.CountKilled()==2u &&
           initial.kills.at(1u).count(55u)==1u &&
           initial.kills.at(1u).count(300u)==1u);
    assert(initial.shown_map==1u && initial.shown.at(55u)==3u &&
           initial.map_state_bits.size()==1250u &&
           initial.return_point==-12 && initial.return_point_map==1u &&
           initial.hp.at(0x123456789ull).enemies.at(55u).value==-51 &&
           initial.hp.at(0x123456789ull).enemies.at(55u).max==100 &&
           initial.snapshot_recent_flags.size()==1u &&
           initial.live_flags_seen==0u && initial.after_wipe);
    // Source-backed original WorldLogKind:
    // Kill 1, Unkill 2, ShownMap 3, Shown 16, MapStateMap 7,
    // MapFlagOn 8, HpSource 10, HpValue 11, FlagSet 5, ReturnPoint 14.
    const auto delta=Batch(19u,{
        E(10u,1u,1u,777u),E(11u,2u,1u,55u),
        E(12u,3u,2u),E(13u,16u,2u,42u,7u),
        E(14u,7u,2u),E(15u,8u,2u,6u),
        E(16u,10u,2u,1u,2u),
        E(17u,11u,200u,42u,static_cast<std::uint32_t>(-44)),
        E(18u,5u,2u,1000u,1u),E(19u,14u,2u,3000u)
    });
    assert(staged.StageEntries(delta,77u,19u,10u,19u,10u));
    assert(projection.Rebuild(staged));
    const auto& updated=projection.View();
    assert(updated.applied==19u && updated.game_applied==0u);
    assert(updated.kills.at(1u).count(777u)==1u &&
           updated.kills.at(1u).count(55u)==0u &&
           updated.CountKilled()==2u);
    assert(updated.shown_map==2u && updated.shown.at(42u)==7u &&
           updated.map_state_map==2u &&
           updated.map_state_bits.size()==1250u &&
           (updated.map_state_bits[0]&2u)!=0u);
    assert(updated.hp.at(3u).enemies.at(42u).value==-44 &&
           updated.hp.at(3u).enemies.at(42u).max==200 &&
           updated.live_flags_seen==1u);
    assert(updated.return_point==3000 && updated.return_point_map==2u);
    // Replayed seq19 is skipped: only the new Unkill(seq20) is applied.
    const auto overlap=Batch(20u,{
        E(19u,14u,99u,123u),E(20u,2u,1u,300u)
    });
    assert(staged.StageEntries(overlap,77u,20u,19u,20u,2u));
    assert(projection.Rebuild(staged));
    const auto& final=projection.View();
    assert(final.applied==20u && final.CountKilled()==1u &&
           final.return_point==3000 && final.return_point_map==2u &&
           final.game_applied==0u);
    staged.Revoke();
    assert(!projection.Rebuild(staged) && !projection.Ready() &&
           projection.View().applied==0u &&
           projection.View().kills.empty());
    std::puts("SHYT_V426_YT_TYPED_READ_ONLY_WORLD_PROJECTION_PASS");
}
