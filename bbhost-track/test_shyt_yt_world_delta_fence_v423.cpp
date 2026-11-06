// SPDX-License-Identifier: GPL-2.0-or-later
#include "shyt_yt_world_delta_fence_v423.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
using Fence=SeamlessHunt::YtWorldDeltaFenceV423;
using Verdict=Fence::Verdict;
int main() {
    Fence normal;
    assert(!normal.Arm(0u,0u));
    assert(normal.Observe(99u,0u,0u,0u,0u)==Verdict::Unbound);
    assert(normal.Arm(77u,9u));
    assert(!normal.Arm(77u,9u));
    assert(normal.Epoch()==77u && normal.Cursor()==9u);
    // Replay from the original server's previous log snapshot: do not
    // rewind even when old Entry payloads arrived after the snapshot.
    assert(normal.Observe(77u,9u,7u,8u,2u)==Verdict::Replay);
    assert(normal.Cursor()==9u && !normal.Behind());
    assert(normal.Observe(77u,9u,0u,0u,0u)==Verdict::Heartbeat);
    // The server's advertised last may include further queued batches.
    assert(normal.Observe(77u,13u,10u,11u,2u)==Verdict::Advanced);
    assert(normal.Cursor()==11u && normal.ServerLast()==13u &&
           normal.Behind());
    // A safe overlapping replay can advance only the new tail.
    assert(normal.Observe(77u,13u,11u,13u,3u)==Verdict::Advanced);
    assert(normal.Cursor()==13u && !normal.Behind());
    assert(normal.Observe(77u,13u,0u,0u,0u)==Verdict::Heartbeat);
    assert(normal.Observe(77u,13u,11u,12u,2u)==Verdict::Replay);
    assert(normal.Stats().advanced==2u && normal.Stats().replays==2u &&
           normal.Stats().heartbeats==2u);
    // There is no room for an automatic rejoin or game-level authorization.
    normal.Revoke();
    assert(!normal.Armed() && !normal.Arm(77u,13u));

    Fence gap;
    assert(gap.Arm(88u,5u));
    assert(gap.Observe(88u,10u,8u,10u,3u)==Verdict::Gap);
    assert(!gap.Armed() && gap.Stats().contexts_revoked==1u);
    assert(gap.Observe(88u,10u,6u,10u,5u)==Verdict::Unbound);

    Fence heartbeat_gap;
    assert(heartbeat_gap.Arm(88u,5u));
    assert(heartbeat_gap.Observe(88u,6u,0u,0u,0u)==Verdict::Gap);
    assert(!heartbeat_gap.Armed());

    Fence epoch_change;
    assert(epoch_change.Arm(90u,6u));
    assert(epoch_change.Observe(91u,6u,0u,0u,0u)==Verdict::EpochChanged);
    assert(!epoch_change.Armed() && epoch_change.Stats().epoch_changes==1u);

    Fence invalid;
    assert(invalid.Arm(100u,6u));
    assert(invalid.Observe(100u,10u,7u,9u,2u)==Verdict::Invalid);
    assert(!invalid.Armed());
    Fence future_seq;
    assert(future_seq.Arm(101u,6u));
    assert(future_seq.Observe(101u,8u,7u,9u,3u)==Verdict::Invalid);
    Fence illegal_heartbeat;
    assert(illegal_heartbeat.Arm(102u,6u));
    assert(illegal_heartbeat.Observe(102u,6u,5u,0u,0u)==Verdict::Invalid);
    Fence max_cursor;
    assert(max_cursor.Arm(103u,UINT64_MAX));
    assert(max_cursor.Observe(103u,UINT64_MAX,1u,2u,2u)==Verdict::Replay);
    assert(max_cursor.Observe(103u,UINT64_MAX,0u,0u,0u)==Verdict::Heartbeat);
    // The upper bound is never incremented or allowed to wrap.
    Fence absurd_count;
    assert(absurd_count.Arm(104u,0u));
    assert(absurd_count.Observe(104u,300u,1u,257u,257u)==Verdict::Invalid);

    std::puts("SHYT_V423_YT_WORLD_DELTA_EPOCH_GAP_REPLAY_FENCE_PASS");
}
