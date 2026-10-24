// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_hybrid_selector.hpp"
#include <cassert>
#include <cstdint>
using namespace SeamlessHunt::Hybrid;

static Grant eligible() {
    Grant g{};
    g.session_epoch = 42;
    g.peer_binding = 91;
    g.valid_until_ms = 60000;
    g.verified_server_authorization = true;
    g.local_consent = true;
    g.peer_consent = true;
    g.protocol_compatible = true;
    return g;
}
int main() {
    Selector peer;
    assert(peer.Choose(true, 0) == Path::Relay);
    auto g = eligible();
    for (unsigned condition = 0; condition < 4; ++condition) {
        auto bad = g;
        if (condition == 0) bad.verified_server_authorization = false;
        if (condition == 1) bad.local_consent = false;
        if (condition == 2) bad.peer_consent = false;
        if (condition == 3) bad.protocol_compatible = false;
        assert(!peer.Begin(bad, 100));
        assert(peer.Choose(true, 101) == Path::Relay);
    }
    auto zero = g;
    zero.session_epoch = 0;
    assert(!peer.Begin(zero, 100));
    zero = g; zero.peer_binding = 0;
    assert(!peer.Begin(zero, 100));
    zero = g; zero.valid_until_ms = 100;
    assert(!peer.Begin(zero, 100));
    assert(peer.Begin(g, 100));
    assert(peer.phase() == Phase::Probing);
    assert(!peer.VerifiedProbe(42, 1, false, 150)); // untrusted
    assert(!peer.VerifiedProbe(41, 1, true, 150));  // old session
    assert(peer.VerifiedProbe(42, 1, true, 200));
    assert(!peer.VerifiedProbe(42, 1, true, 220)); // replay
    assert(!peer.VerifiedProbe(42, 0, true, 230));
    assert(peer.Choose(true, 250) == Path::Relay);
    assert(peer.VerifiedProbe(42, 2, true, 320));
    assert(peer.Choose(true, 325) == Path::Relay);
    assert(peer.VerifiedProbe(42, 3, true, 400));
    assert(peer.phase() == Phase::DirectReady);
    assert(peer.Choose(false, 500) == Path::Relay); // world/map/owner-sensitive
    assert(peer.Choose(true, 500) == Path::Direct);
    assert(peer.Choose(true, 2400) == Path::Direct);
    assert(peer.Choose(true, 2401) == Path::Relay); // heartbeat failed
    assert(peer.phase() == Phase::Cooldown);
    assert(!peer.Retry(12400));
    assert(peer.Retry(12401));
    assert(peer.Choose(true, 12420) == Path::Relay);
    assert(!peer.VerifiedProbe(42, 3, false, 12425));
    assert(peer.VerifiedProbe(42, 10, true, 12430));
    assert(peer.VerifiedProbe(42, 11, true, 12440));
    assert(peer.VerifiedProbe(42, 12, true, 12450));
    assert(peer.Choose(true, 12460) == Path::Direct);
    assert(!peer.VerifiedDirectHeartbeat(41, 13, true, 12470)); // old match
    assert(!peer.VerifiedDirectHeartbeat(42, 12, true, 12470)); // replay
    assert(!peer.VerifiedDirectHeartbeat(42, 13, false, 12470)); // forgery
    assert(peer.VerifiedDirectHeartbeat(42, 13, true, 12500));
    assert(peer.Choose(true, 14499) == Path::Direct); // authenticated heartbeat
    assert(peer.Choose(true, 14501) == Path::Relay);  // stale again
    peer.Reset(); // leave group, ban, password change, new host
    assert(peer.Choose(true, 12470) == Path::Relay);
    assert(!peer.VerifiedProbe(42, 13, true, 12470));
    // Expiry cannot preserve a previously authorized direct session.
    assert(peer.Begin(g, 59000));
    assert(!peer.VerifiedProbe(42, 1, true, 65001));
    assert(peer.Choose(true, 65001) == Path::Relay);
    assert(peer.phase() == Phase::RelayOnly);
    // A stalled NAT hole punch must retry only after cooldown.
    assert(peer.Begin(g, 700));
    assert(peer.Choose(true, 5701) == Path::Relay);
    assert(peer.phase() == Phase::Cooldown);
    assert(!peer.Retry(15700));
    assert(peer.Retry(15701));
    peer.Reset();
    // Late probes outside rendezvous window never establish direct.
    assert(peer.Begin(g, 1000));
    assert(!peer.VerifiedProbe(42, 1, true, 6001));
    assert(peer.Choose(true, 6002) == Path::Relay);
    return 0;
}
