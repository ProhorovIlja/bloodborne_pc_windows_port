# Five total hunters: co-op + invasion seat policy

Status: design contract and original Qt server admission test, **NOT** evidence of playable
multi-invader Bloodborne or WAN P2P. Main delivery still PR #17; original Qt server
functional/load regressions are in **existing PR #37**. No deployment to Fornex.

## Source facts (2026-10-29)

- **Sony's original 2015 Bloodborne**: maximum three participants, with up to
  two guests/invaders in some areas.
  https://blog.playstation.com/2015/04/03/bloodborne-how-to-make-the-most-of-multiplayer/
- **CLSAMG22/BBSC**: up to five co-op hunters (one host/four guests), Bloodlust
  Bell for invading and Duel Bell to toggle within-party PvP. Its public
  documentation does **not** demonstrate three simultaneous hostile invaders
  or their exact native kinds/signs.
  https://github.com/CLSAMG22/BBSC
- **Official Yharnam Together 1.3.0 pinned source**:
  `server/src/bloodborne_world.h` stores `std::map<QString, Invasion>`,
  exactly **one invader per world**, with `target.invaded` excluding a second.
  `docs/INVASIONS.md` calls `InvasionKind=0xFFFFFFFF` and `InvasionSign=4`
  **unconfirmed placeholders** awaiting original hostile packet/eboot capture.
  The shipped team lobby supports 4, our source-staged team supports 5 and
  assigns co-op guest signs `7,6,5,4`. Invaders do **not** become members of
  the co-op team/world, do not win co-op rewards and do not count for wipes.
  https://github.com/lKaniel/bloodborne-server/blob/0645740/docs/INVASIONS.md

## Correct single-simulation capacity model

A **session** has at most **five actual player bodies**. The host is one of the
co-operators. The number of invading players occupies remaining real slots;
it does not increase the five-player cap.

| Total co-op including host | Hostile invaders | Total | State |
|---:|---:|---:|---|
| 5 | 0 | 5 | Five-hunter server lobby and original C++ tests verified; five real games not yet shown |
| 4 | 1 | 5 | Single-invader server admission C++ tests verified; native hostile rendering still experimental |
| 3 | 2 | 5 | Future candidate, **not implemented** in current YT server/game |
| 2 | 3 | 5 | Future candidate, **not implemented**; requires native sign/type/slot proof |
| 5 | 1 | 6 | Always refuse: overflow |
| 4 | 2 | 6 | Always refuse: overflow |
| 3 | 3 | 6 | Always refuse: overflow |

The four rows are **illustrative maximum-fill configurations**, not mandatory
occupancy: a session with 2 co-op and 1 invader is fine once ordinary PvP
itself is verified. A solo host can also be a potential PvP target under
original Bloodborne rules, subject to explicit consent/policy. Do not prevent
it solely because the examples start at two co-operators.

There are three distinct budgets:

1. **Absolute game/session cap:** `cooperators + active_invaders <= 5`.
   No actor bypasses this, including disconnected team members with reserved
   places, an invader in 10-second matchmaking notice, or join/host migration.
2. **Server implementation cap NOW:** `active_invaders + pending_invaders <= 1`
   for each world. Its live model cannot represent two `Invasion` objects.
   `SupportsCurrentServerInvasion` must fail closed on requests beyond one.
3. **Potential expanded PvP cap:** **up to three hostile participants only if
   separately proven** by native game captures, per-hostile session signs,
   correct hostile character type, packet routes, lifecycles, network ACK
   behavior, UI and actual five-game tests. The pure
   `FitsFiveHunterRoles(3,2)`/`(2,3)` static asserts establish only integer
   budget consistency, never enable either mode.

## Concrete implementation gates before multi-invader goes live

- One authoritative world may hold several **independently identified**
  invasions, each with ID, signed-in invader identity, slot, signed session,
  current map, timeout, enemy-owner scope and own cooldown. Current
  `map<QString,Invasion>` is NOT this structure.
- Allocate slots atomically against **all reserved co-op signs and every
  pending or active hostile sign**. Never reuse sign `4` occupied by a
  fourth co-op guest, or produce sign `0`, `3`, etc. without observing
  actual native game acceptance. Validate native `kind`, team, labels and
  *mutual visibility* from a genuine Sinister Bell capture.
- Recheck world/leader consent, boss rules, count and every occupied slot
  just before granting each invasion. Host can disable invasions at any
  time. Do not invite into the Dream or boss fights under current policy.
- Revoking one invader must revoke **only that invader's** routing/keys,
  without destroying other invaders' state or co-op gameplay. A party joining
  its fifth member must not produce a sixth actor. This can initially mean
  cancelling PvP; client despawn and ACK must be verified before release.
- Multi-hostile damage/kill/target semantics, different teams including
  invader-against-invader, friendly fire, boss possession, Duel Bell modes,
  HUD party roles, rewards and save isolation are separately gated features.
  No boss-possession mode is implemented now.
- Hybrid P2P must encrypt each pair, carry signed server identity and
  NAT-ready proof, preserve server-owned world state and GameLink reliable
  ACK, and automatically fall back to relay. No live Direct bypass of
  the authoritative five-seat policy.
- Finish original native client + launcher + matching Linux and Windows
  server build, then real 2-PC and five-client tests, capacity/loss/latency
  on the 4-vCPU Fornex configuration **before** production rollout.

## Current change

`tools/poc/yharnam/yt130-reference/stage_five_hunter_invasion_guard.py`
stages the original upstream invasion vacancy/notice/routing patches.
`SupportsCurrentServerInvasion` checks the live one-invader implementation,
while `FitsFiveHunterRoles` records requested upper-bound combinations.
The original Qt world tests cover mid-notice fifth joining, legitimate
four-co-op+one-invader, and late fifth joining after invasion starts.
Targeted Qt CI is `.github/workflows/shyt-yt130-five-invasion-fast-gate.yml`.

**No public PvP and no server-capacity boast from these tests.**
