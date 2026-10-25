#!/usr/bin/env python3
"""V77 monotonic per-game-link generation prevents P2P world-version ABA.

Runs after V76 and original Qt co-op tests. Pure in-memory server-side state,
no new protocol/port/db, P2P still disabled without TLS control channel.
"""
from __future__ import annotations
H="server/src/bloodborne_world.h"
CPP="server/src/bloodborne_world.cpp"
TEST="server/tests/test_bloodborne_world.cpp"
def one(s,a,b,label):
    n=s.count(a)
    if n!=1:raise ValueError(f"V77 {label}: expected one anchor found {n}")
    return s.replace(a,b,1)
def patch(f):
    if set(f)!={H,CPP,TEST}:raise ValueError("V77 requires exact Qt composed world & tests")
    h,cpp,t=(f[x] for x in (H,CPP,TEST))
    h=one(h,
'''        bool direct_p2p_opt_in = false; // old clients are relay-only
''',
'''        bool direct_p2p_opt_in = false; // old clients are relay-only
        quint64 direct_state_serial=0; // server-only grant revocation generation
''',"member generation")
    h=one(h,
'''    std::map<quint64, Member> members; // by link (Endpoint::Key)
''',
'''    quint64 direct_next_serial=0; // NEVER from a game/client payload
    bool BumpDirectSerial(Member& member) noexcept {
        if (direct_next_serial==std::numeric_limits<quint64>::max()) {
            direct_next_serial=0; // exhausted; all grants must remain invalid
            member.direct_state_serial=0;
            return false;
        }
        member.direct_state_serial=++direct_next_serial;
        return true;
    }
    std::map<quint64, Member> members; // by link (Endpoint::Key)
''',"server single serial allocator")
    h=one(h,
'''#include <map>
''',
'''#include <limits>
#include <map>
''',"max serial include")
    cpp=one(cpp,
'''    member.direct_p2p_opt_in = false;
''',
'''    member.direct_p2p_opt_in = false;
    // Even a refused Hello permanently invalidates the previous snapshot.
    // Increment only on Hello, map transition or link restart, not each
    // gameplay datagram, so no server-side hot-path crypto overhead.
    (void)BumpDirectSerial(member);
''',"invalidate on game Hello")
    cpp=one(cpp,
'''    case bbcoop::Envelope::kMap: {
        member.map = envelope.map().map();
''',
'''    case bbcoop::Envelope::kMap: {
        if(member.map!=envelope.map().map())
            (void)BumpDirectSerial(member);
        member.map = envelope.map().map();
''',"map change new session scope")
    cpp=one(cpp,
'''    if (member.stream.TakeRestarted()) {
        result.log.append(QStringLiteral("party world: %1's game started over: waiting for its "
''',
'''    if (member.stream.TakeRestarted()) {
        member.direct_p2p_opt_in=false;
        (void)BumpDirectSerial(member);
        result.log.append(QStringLiteral("party world: %1's game started over: waiting for its "
''',"protocol restart revokes past consent and scopes")
    cpp=one(cpp,
'''    const std::uint64_t reset_revision=reset==party.map_reset_ms.end() ? 0 :
''',
'''    const std::uint64_t reset_revision=reset==party.map_reset_ms.end() ? 0 :
''',"world revision remains pinned")
    needle='''    return SeamlessHunt::Hybrid::BoundWorldRevision(input);
}'''
    replacement='''    const auto world_revision=SeamlessHunt::Hybrid::BoundWorldRevision(input);
    // V77: identical map/team/owner after a leave/rejoin must never allow
    // an older server grant to match again. Membership generations are
    // allocated by this server (not client Hello.run), and are symmetric.
    if(!world_revision || !first.direct_state_serial || !second.direct_state_serial ||
       direct_next_serial==0) return 0;
    const auto lo=std::min(first.direct_state_serial,second.direct_state_serial);
    const auto hi=std::max(first.direct_state_serial,second.direct_state_serial);
    auto revision=SeamlessHunt::Hybrid::RevisionNumber(world_revision,lo);
    revision=SeamlessHunt::Hybrid::RevisionNumber(revision,hi);
    return revision ? revision : 1;
}'''
    cpp=one(cpp,needle,replacement,"pair generation prevents ABA")
    t=one(t,
'''  a.Map(0,now+20);
  Pump(service,games,now+20);
''',
'''  a.Map(0,now+20);
  Pump(service,games,now+20);
''',"original map test anchor")
    t=one(t,
'''  a.Map(Yharnam,now+30);
  Pump(service,games,now+30);
  CHECK(service.PairDirectConsent("host","guest"));
''',
'''  a.Map(Yharnam,now+30);
  Pump(service,games,now+30);
  CHECK(service.PairDirectConsent("host","guest"));
  const auto returned=service.CaptureDirectPairScope("host","guest");
  CHECK(returned.has_value());
  CHECK(returned->world_revision!=captured->world_revision); // no ABA
  CHECK(returned->first_virtual==captured->first_virtual);
''',"same map after return changes server epoch")
    t=one(t,
'''  b.Hello(now+50,Party,true);
  Pump(service,games,now+50);
  CHECK(service.PairDirectConsent("host","guest"));
''',
'''  b.Hello(now+50,Party,true);
  Pump(service,games,now+50);
  CHECK(service.PairDirectConsent("host","guest"));
  const auto rejoined=service.CaptureDirectPairScope("host","guest");
  CHECK(rejoined.has_value());
  CHECK(rejoined->world_revision!=returned->world_revision); // opt-out/re-Hello ABA
''',"same party and map after rehello must revoke old grant")
    return {H:h,CPP:cpp,TEST:t}
