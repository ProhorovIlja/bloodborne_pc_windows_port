#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_pvp_privacy.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::PvpPrivacy;
int main() {
    constexpr Member host{44,Side::Hunters,9,true};
    constexpr Member cooperator{44,Side::Hunters,9,true};
    constexpr Member invader_a{44,Side::Invaders,9,true};
    constexpr Member invader_b{44,Side::Invaders,9,true};
    constexpr Member other_room{45,Side::Hunters,9,true};
    constexpr Member legacy{44,Side::Invaders,8,true};
    constexpr Member unknown{44,Side::Invaders,9,false};
    constexpr Member spectator{44,Side::Spectators,9,true};
    static_assert(SameSquad(host,cooperator));
    static_assert(SameSquad(invader_a,invader_b));
    static_assert(!SameSquad(host,invader_a));
    static_assert(!SameSquad(host,other_room));
    for(const Feed f : {Feed::PartyHud,Feed::Compass,Feed::Map,Feed::PartyVitals,Feed::PreciseCoordinates}) {
        assert(MaySendPartyTelemetry(f,host,cooperator));
        assert(MaySendPartyTelemetry(f,invader_a,invader_b));
        assert(!MaySendPartyTelemetry(f,host,invader_a));
        assert(!MaySendPartyTelemetry(f,invader_a,host));
        assert(!MaySendPartyTelemetry(f,host,spectator));
        assert(!MaySendPartyTelemetry(f,invader_a,legacy));
        assert(!MaySendPartyTelemetry(f,invader_a,unknown));
    }
    assert(!MaySendPartyTelemetry(Feed::CoarseLastSeen,host,cooperator));
    assert(!MayShareCoarseSpot(host,invader_a,false,0));
    assert(MayShareCoarseSpot(host,invader_a,true,0));
    assert(MayShareCoarseSpot(invader_a,host,true,1500));
    assert(!MayShareCoarseSpot(invader_a,host,true,1501));
    assert(!MayShareCoarseSpot(invader_a,host,true,-1));
    assert(!MayShareCoarseSpot(invader_a,legacy,true,0));
    assert(!MayFreecam(true,host));
    assert(!MayFreecam(true,invader_a));
    assert(!MayFreecam(true,spectator));
    assert(MayFreecam(false,host));
    std::cout<<"PASS: faction-private co-op/invasion HUD and short verified spotting\n";
}
