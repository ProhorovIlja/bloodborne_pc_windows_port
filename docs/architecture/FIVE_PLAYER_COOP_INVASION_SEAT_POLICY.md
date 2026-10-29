# Five total hunters: co-op + invasion seat policy

Status: **REQUIRED first public release feature**, not a later optional expansion.
Native game and Qt server source candidates are actively being integrated into
the same 5-total-body session model. Not playable or validated yet.
The original Qt server/current upstream native-game source gates are existing
PR #37; the Windows game/launcher and secure Direct build are existing PR #17.
No production Fornex change.

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
| 3 | 2 | 5 | **Required at launch**; multi-invader original Qt server and native-game source patch under CI, not yet a playable build |
| 2 | 3 | 5 | **Required at launch**; up to 3 independent server+client hostile IDs, native kind/sign proof and five actual game clients required |
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
2. **Original vanilla YT 1.3 cap:** one invader per world. Our V108
   original Qt staged candidate replaces it with a bounded map keyed by
   **world + invasion ID**, with `active + pending <= 3`, unique
   reserved signs and sign-collision cleanup on cooperative arrivals.
   Original Qt C++ compilation and 2+3/3+2 functional tests are required
   before marking the server implementation verified.
3. **Native game required cap:** V107 original native game
   `InvadedTeam` has a bounded three-hostile ID ledger on upstream
   `0645740a`, preserving each visitor's notice/join/end independently.
   The prior Windows composition PIN `77e350` predates the **entire**
   invasion game subsystem: do not claim the native feature is present
   until a compatible complete upstream rebase/backport builds the true
   native Windows game. After that, actual 2+3 and 3+2 playtests must
   confirm hostile rendering, mutual PvP hits, native sign/kind, UI,
   death handling and save isolation, not only source tests.

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
- **Required at first release:** correct hostile damage, kill/target
  semantics, invader-against-invader routing, friendly-fire policy, all
  invader names/IDs on the HUD, host PvP toggle, independent disconnect
  and respawn, Duel Bell compatibility and personal save isolation.
  **Optional later:** controlling an in-progress boss as an invader and
  expanded event/reward experiments. No boss-possession mode is implemented.
- Hybrid P2P must encrypt each pair, carry signed server identity and
  NAT-ready proof, preserve server-owned world state and GameLink reliable
  ACK, and automatically fall back to relay. No live Direct bypass of
  the authoritative five-seat policy.
- Finish original native client + launcher + matching Linux and Windows
  server build, then real 2-PC and five-client tests, capacity/loss/latency
  on the 4-vCPU Fornex configuration **before** production rollout.

## Current implementation work (not a release claim)

- `stage_five_hunter_invasion_guard.py`: original Qt five-person admission,
  10-second notice recheck and host/party overflow protection.
- `stage_multi_invader_server_v108.py`: original Qt per-world three-invasion
  ledger, unique reservation of signs 4–7, own timeout/vitals/end/owner
  routing, same-world hostile-to-hostile game channels, exact-slot collision
  cleanup. Includes original Qt scenarios 2+3 and 3+2, plus selective
  invader death, opt-out and fifth cooperator admission tests.
- `patch_original_multi_invader_client_v107.py`: actual newer upstream
  game's native `InvadedTeam` replaced with per-ID three-hostile ledger
  and an original native game gtest; tested only after integration into
  an updated native build.
- CI: `.github/workflows/shyt-yt130-five-invasion-fast-gate.yml`
  composes disposable source on upstream SHA `0645740a` and compiles
  original Qt tests. The new server/game multi-visitor code is NOT
  production until latest CI passes and native gameplay proves behavior.
- PR #17's `77e350` Windows game base remains a specific release
  blocker. AES-GCM/P2P can pass while native invasions are absent:
  **such a binary is not feature-complete and cannot be advertised as
  the target release.**

**No five-game PvP gameplay, verified hostile sign/kind, or real WAN Direct
has been demonstrated yet. Do not deploy to production Fornex.**
