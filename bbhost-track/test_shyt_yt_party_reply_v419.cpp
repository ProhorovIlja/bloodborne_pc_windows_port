// SPDX-License-Identifier: GPL-2.0-or-later
#include "shyt_yt_party_reply_v419.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
using Tracker = SeamlessHunt::YtPartyReplyV419;
int main() {
    Tracker normal;
    assert(normal.OnAuthenticatedWelcome(true,100,true)==Tracker::Reply::Unbound);
    assert(normal.Arm("world:one",1,707,200));
    assert(!normal.Arm("world:one",1,707,200));
    assert(normal.Pending() && normal.Party()=="world:one" &&
           normal.Slot()==1 && normal.Run()==707);
    assert(normal.OnAuthenticatedWelcome(true,210,true)==Tracker::Reply::CorrelatedCandidate);
    assert(!normal.Pending() && normal.CandidateAwaitingSnapshot());
    assert(normal.OnAuthenticatedWelcome(true,220,true)==Tracker::Reply::Unbound);
    assert(!normal.CandidateAwaitingSnapshot());
    assert(!normal.Arm("world:one",1,707,230)); // one opt-in per session
    const auto normal_stats=normal.Stats();
    assert(normal_stats.party_hellos_sent==1 && normal_stats.replies_correlated==1 &&
           normal_stats.replies_unbound==2 && normal_stats.contexts_revoked==1);

    Tracker refused;
    assert(refused.Arm("world:two",0,900,1000));
    assert(refused.OnAuthenticatedWelcome(false,1001,true)==Tracker::Reply::Refused);
    assert(!refused.Pending() && !refused.CandidateAwaitingSnapshot());
    assert(refused.Stats().replies_refused==1);

    Tracker expired;
    assert(expired.Arm("world:three",2,123,500));
    assert(expired.OnAuthenticatedWelcome(true,500+Tracker::ReplyWindowMs+1,true)==Tracker::Reply::Unbound);
    assert(!expired.Pending() && expired.Stats().contexts_revoked==1);

    Tracker rewind;
    assert(rewind.Arm("world:four",3,444,1000));
    assert(rewind.OnAuthenticatedWelcome(true,999,true)==Tracker::Reply::Unbound);
    assert(!rewind.CandidateAwaitingSnapshot());

    Tracker roster_change;
    assert(roster_change.Arm("world:five",4,555,2000));
    roster_change.Revoke();
    assert(roster_change.OnAuthenticatedWelcome(true,2010,true)==Tracker::Reply::Unbound);
    assert(roster_change.Stats().contexts_revoked==1);

    Tracker changed_slot;
    assert(changed_slot.Arm("world:six",0,666,3000));
    assert(changed_slot.OnAuthenticatedWelcome(true,3001,false)==Tracker::Reply::Unbound);
    assert(!changed_slot.CandidateAwaitingSnapshot());

    Tracker upper_bound;
    assert(upper_bound.Arm("world:seven",1,777,10));
    assert(upper_bound.OnAuthenticatedWelcome(true,10+Tracker::ReplyWindowMs,true)==Tracker::Reply::CorrelatedCandidate);
    upper_bound.Revoke();
    assert(!upper_bound.CandidateAwaitingSnapshot());

    Tracker malformed;
    assert(!malformed.Arm("",1,1,1));
    assert(!malformed.Arm("world:bad",1,0,1));
    assert(!malformed.Arm(std::string(256,'x'),1,1,1));
    std::puts("SHYT_V419_PARTY_REPLY_CONTEXT_FENCE_PASS");
}
