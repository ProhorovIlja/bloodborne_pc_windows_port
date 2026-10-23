#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_session_guard.hpp"
#include <array>
#include <cassert>
#include <climits>
#include <iostream>
using namespace SeamlessHunt::SessionGuard;
int main() {
    VitalsReport v{.vital=1,.hp=1000,.max_hp=1200,.vials=20,.bullets=15,
                   .has_position=true,.x=-100,.y=2.5f,.z=55};
    assert(SafeVitalValues(v));
    v.x=std::numeric_limits<float>::infinity(); assert(!SafeVitalValues(v)); v.x=0;
    v.y=std::numeric_limits<float>::quiet_NaN(); assert(!SafeVitalValues(v)); v.y=2;
    v.vital=5; assert(!SafeVitalValues(v)); v.vital=1;
    v.max_hp=INT_MAX; assert(!SafeVitalValues(v)); v.max_hp=1200;
    v.vials=65535; assert(!SafeVitalValues(v)); v.vials=20;
    assert(SafeVitalValues(v));
    const std::array good{ReviveHit{"hunter_a", 3, 700}, ReviveHit{"hunter_b", 1, 900}};
    assert(SafeReviveHits(good));
    const std::array duplicates{ReviveHit{"hunter_a", 3, 200}, ReviveHit{"hunter_a", 3, 900}};
    assert(!SafeReviveHits(duplicates));
    const std::array huge{ReviveHit{"hunter_a", 3, 100'000}};
    assert(!SafeReviveHits(huge));
    assert(AddReviveDamage(UINT32_MAX-2, 200)==UINT32_MAX);
    assert(AddReviveDamage(100, 500)==600);
    assert(SafeWireText("hunter_01", 96));
    assert(!SafeWireText("bad\nname", 96));
    assert(!SafeWireText("", 96));
    assert(!SafeWireText("abcdef", 5));
    assert(ShouldAudit(100,0));
    assert(!ShouldAudit(201,100));
    assert(ShouldAudit(10'100,100));
    std::cout<<"PASS: bounded no-allocation session sanity, saturation, sparse audit\n";
}
