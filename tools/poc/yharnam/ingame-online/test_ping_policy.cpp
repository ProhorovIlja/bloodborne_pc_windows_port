// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "ping_policy.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::InGame;
int main(){
    const auto now=std::chrono::steady_clock::now();
    PingSamples sample{{32,34,36},{90,95,100},true,true,now};
    PingFilter f;f.maximum_ms=50;
    auto direct=MatchPing(sample,f,now);
    assert(direct.matches && direct.path==PingPath::DirectOnly && direct.measured_ms==34);
    f.maximum_ms=30;
    assert(!MatchPing(sample,f,now).matches);
    f.path=PingPath::RelayOnly;f.maximum_ms=110;
    assert(MatchPing(sample,f,now).path==PingPath::RelayOnly);
    sample.direct_verified=false;
    f.path=PingPath::DirectOnly;f.maximum_ms=90;
    assert(!MatchPing(sample,f,now).matches);
    f.maximum_ms=100;
    assert(!MatchPing(sample,f,now).matches);
    // Even with fallback enabled a request for DIRECT-only never accepts relay.
    f.allow_relay_fallback=true;
    f.maximum_ms=100;
    assert(!MatchPing(sample,f,now).matches);
    f.path=PingPath::Any;
    assert(MatchPing(sample,f,now).matches);
    f.path=PingPath::DirectOnly;
    f.maximum_ms.reset(); // unknown direct RTT cannot pass just because cap is absent
    assert(!MatchPing(sample,f,now).matches);
    f.allow_relay_fallback=false;
    assert(!MatchPing(sample,f,now).matches);
    sample.direct_verified=true;sample.authenticated=false;
    assert(!MatchPing(sample,f,now).matches);
    sample.authenticated=true;
    assert(!MatchPing(sample,f,now+std::chrono::seconds(16)).matches);
    assert(QualityFor(30)==PingQuality::Excellent);
    assert(QualityFor(200)==PingQuality::VeryHigh);
    std::cout<<"PASS: peer RTT direct/relay, strict ping filter, stale/unknown samples\n";
}
