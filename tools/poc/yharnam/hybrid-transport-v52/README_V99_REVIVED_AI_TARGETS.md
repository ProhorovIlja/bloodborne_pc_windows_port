# V99: revived teammates regain boss AI targeting (original Yharnam Together)

**Source-only DRAFT PR17, original native game only.** Based on the publicly documented original [Kaniel PR #413](https://github.com/lKaniel/bloodborne-server/pull/413), where two guests were never chosen by Martyr Logarius in the host's second attempt despite being alive. The host-side copy still had character controller info +0x18 bit 0 set following their actual deaths. The game's target-selection AI mode 0 skips such marked players until the host reloads the map.

## Backport and safeguards

`patch_upstream_stale_death_v99.py` is an exact-anchored **five-file atomic transform** for the immutable original `77e350743a7cb4524cfcc1782fb6e3af64e25b15` native game sources. Staged in `unified-v9/compose_sources.py` after V97 (Doll flag 6700 is local) and V98 (dead-body hits cannot instantly down a player on lamp respawn).

The game-owned pure `StaleDeathMarks` policy tracks a candidate's handle, internal info-pointer identity, and current map visit. The same alive/marked/non-invader/non-downed character must appear **continuously for 3000 ms**. The timer is discarded when the body is absent, no longer marked, dead, downed, an invader, the info pointer changes, the handle changes, the map visit changes, or the party ends. This is stricter than counting only a handle, since handles can be reused across map loads.

`ClearStaleDeathMarks` runs **on the original game thread** and reads only local game-owned party state. It checks the current co-op session, validates original control/info pointer mappings and write access, independently verifies invader/death/down status, and re-reads live `OtherPlayers()` plus character handle/info pointer and world visit immediately before clearing exactly info +0x18 bit 0. The controller keeps the other bits untouched, and game/logging state remains the original authority. It does not respond to any direct network-supplied packet and never adds a new worker.

`TargetCandidateBlock` also explains the original enemy targeting exclusion instead of incorrectly saying the revived hunter is eligible for AI targeting. All changes are internal to native game memory and the existing game tick, with NO change to shadNet LinkServer, encrypted grants, P2P socket routing, server data, user account or save files.

## Tests and release gates

- `test_patch_upstream_stale_death_v99.py`: exact five-file transactional anchors, refusal to double-apply, source drift denial, map/identity/permission safeguards and original game tick.
- `test_stale_death_v99.cpp`: executes **the actual C++ policy extracted from the newly patched original game source**, not a rewritten test implementation. Cases cover 3s threshold, same-handle different pointer, new map visit, dead/downed/invader/unmarked, party exit, clock rollback and re-enter.
- `.github/workflows/shyt-v99-original-game-revived-ai.yml`: immutable original source fetch, actual V97→V98→V99 composition, C++20 compile/run on Windows MSVC and Ubuntu GCC.
- Unified pinned original game source composer and the existing V94/V97/V98 gates must also succeed.

**Not yet verified:** full native Windows renderer link with V99, actual playing two-PC party targeting Logarius, boss-wipe/host migration, real interop with existing Yharnam Together players, or any reduction in relay/VPS load. Do not claim CI PASS or game success until checked. Potential side effects of changing game AI status demand explicit runtime QA on host, guest, invader, ghost and boss scenarios.

Production Fornex, CLS Friends, master, saves, firewall and account databases remain untouched. Hybrid Direct game UDP still OFF.
