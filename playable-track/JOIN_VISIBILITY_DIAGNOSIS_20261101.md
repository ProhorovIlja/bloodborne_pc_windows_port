# Invisible hunter / hot join: what is verified, and next action

**Based on public Yharnam Together source**, not a claim that the original
reporting player's exact bug has been reproduced or fixed.

## Existing upstream fixes: do not duplicate

In original 1.3.1 source `emulator/src/core/bloodborne_join.cpp`,
`RecreateRemotePlayers` restores remote join tasks when a party travels and
`joins_waiting_for_data` tracks joining guests whose data were lost in a
trip. `emulator/src/core/bloodborne_boards.cpp` function
`FinishWaitingJoins` retries channel 0x0A member-data requests and creates
their character only after all required data parts arrive. Original tests
`test_bloodborne_member_data.cpp` cover lost replies, stale data, and
members who leave the map. `test_bloodborne_three_players.cpp` describes
the exact class of symptom, a guest with a nameplate but no body after a
host world transition. A separate `NameUnnamedGuestRole` fix handles
the unrelated `?ActionEventInfo?` label.

## Open upstream hazard: incorrect member-specific map predicate

At public upstream SHA `5d2305ee611ef1e03be39ff925f0da75c9a70393`,
`FinishWaitingJoins` computes one shared `here` boolean:

    view.Fresh() && !view.member.empty() &&
      SomeoneElseStands(view.board.members, view.member, PlayingMap())

That means **any** up teammate on the local map qualifies, even when
`joins_waiting_for_data` contains a *different* target member. With 3-5
hunters there may be another visible teammate while the target has not
arrived or even belongs to a different map. The later member-data reply
might be valid network data yet not proof of that target's presence.
This is a code-level risk inferred from source, **not a proven root cause**
of the reporter's invisible actor.

**Do not directly change the live game memory or force-create an actor.**
First bind each join task's member ref to the corresponding board identity
using existing `SessionMemberBoardName` and the cached online-ID map,
then prove that specific target is `Vital::Up` and on the current map.
Avoid re-running expensive session member-memory scans every tick; the
upstream `SessionNameCache` already implements retry backoff and recheck.
Require a 3-member test where A is local, B stands here, C is elsewhere:
B's presence must *not* satisfy C's waiting task. Add tests for target
arrival, target leaving, stale board, rejoin and 5 players before
proposing the exact engine patch. The displayed HP bar is not sufficient
to establish the game actor exists.

## Safe local diagnostic (not a new network service)

Run **only on the owner's local machine** against a locally trimmed text log:

    python playable-track/inspect_yt131_join_log_v1.py --self-test
    python playable-track/inspect_yt131_join_log_v1.py local-yt-debug.log

The tool scans at most 64 MiB / 500,000 lines, prints no source lines,
addresses, IDs or private packet data, reports number of 'asked', 'create'
and outstanding join task requests. A missing create in the log can simply
mean the log ended early, and a create log is NOT proof that the in-world
character rendered. No full log should ever be sent into ChatGPT or CI.

First compare clean v1.3.1 with the exact CLS merged commit. Keep
Fornex unchanged until two-PC, dual-instance, Hunter's Dream, in-world
hot-join and multi-player regressions pass.

## 2026-11-01: cloned-instance identity ambiguity

The experimental pinned-source join candidate now also sorts the known
online IDs and fails closed if two board participants resolve to the
**same online ID**. When a single-PC multi-instance test reuses one
identity, the session cannot safely infer which body a given member's
pending join task belongs to. We prefer waiting/diagnosing to
creating the wrong person's remote actor. Synthetic tests cover
five distinct IDs, a duplicate among five, and two identical IDs.

This is intentionally conservative and is NOT a complete solution for
legitimate multi-instance testing. A correct future implementation
needs a server-authorized session-instance identity **in addition** to
online ID and slot, plus a life-cycle reset and a two-PC game test.
The patch remains source-only on a clean upstream checkout; no
shipping player build or Fornex server was changed.
