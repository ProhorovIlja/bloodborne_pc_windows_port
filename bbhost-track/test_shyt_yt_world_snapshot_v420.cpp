// SPDX-License-Identifier: GPL-2.0-or-later
#include "shyt_yt_world_snapshot_v420.h"
#include <cassert>
#include <cstdio>
using Fence=SeamlessHunt::YtWorldSnapshotV420;
int main() {
    Fence normal;
    assert(!normal.Arm(0,0)); // no uninitialized world metadata
    assert(!normal.MarkRequested());
    assert(!normal.Observe(90,0));
    assert(normal.Arm(90,7));
    assert(!normal.Arm(90,7));
    assert(normal.CanAsk() && normal.MarkRequested());
    assert(!normal.MarkRequested());
    assert(!normal.Observe(90,6)); // stale log sequence invalidates context
    assert(!normal.Armed() && !normal.AwaitingGameSnapshotConsumer());
    assert(!normal.Arm(90,7)); // no auto-rejoin after failure

    Fence matching;
    assert(matching.Arm(77,0));
    assert(!matching.Observe(77,0)); // must explicitly ask first
    assert(matching.MarkRequested());
    assert(matching.Observe(77,0)); // proto3 omitted last=0
    assert(matching.AwaitingGameSnapshotConsumer());
    assert(!matching.Observe(77,0)); // duplicate is not a new grant
    matching.Revoke();
    assert(!matching.AwaitingGameSnapshotConsumer());
    auto counts=matching.Stats();
    assert(counts.requests_sent==1 && counts.metadata_matching==1 &&
           counts.metadata_unbound==2 && counts.contexts_revoked==1);
    assert(!matching.Arm(77,0));

    Fence wrong_epoch;
    assert(wrong_epoch.Arm(31,0));
    assert(wrong_epoch.MarkRequested());
    assert(!wrong_epoch.Observe(32,100));
    assert(!wrong_epoch.Armed() && wrong_epoch.Stats().metadata_rejected==1);

    Fence advancing;
    assert(advancing.Arm(99,4) && advancing.MarkRequested());
    assert(advancing.Observe(99,8)); // newer world seq same epoch is fine
    assert(advancing.AwaitingGameSnapshotConsumer());
    std::puts("SHYT_V420_ORIGINAL_YT_WORLD_SNAPSHOT_METADATA_FENCE_PASS");
}
