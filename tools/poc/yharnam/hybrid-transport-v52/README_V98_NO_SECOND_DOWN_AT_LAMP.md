# V98: prevent an instant second down after a genuine death and lamp respawn

**Original Yharnam Together native game source only, branch feature/shyt-hybrid-p2p-v52 (DRAFT PR17).** Backported after V97 from upstream original author [PR #410](https://github.com/lKaniel/bloodborne-server/pull/410). No current player saves, live Fornex/CLS Friends/master/database, Discord data or online protocol touched.

## Real issue reproduced by the original project's playtests

October 25, 2026: after choosing Give Up in a downed co-op session, a guest wakes at the last lamp but is immediately downed again before any new enemy hit. The upstream log confirmed the death hook increments a cumulative lethal-catches counter on the 0-HP corpse. Old game code read the counter only in TickStanding, so old events were interpreted as brand-new hits when the hunter woke. A team wipe could trigger the same problem.

## Actual V98 code

* patch_upstream_lethal_catches_v98.py edits FOUR exact native gameplay units in the immutable pinned upstream 77e350743a7cb4524cfcc1782fb6e3af64e25b15, after V97 has already changed party.h and party.cpp: emulator/src/core/bloodborne_party.h, bloodborne_party.cpp, bloodborne_party_death.cpp, bloodborne_re_internal.h. Each source anchor is checked once, and the patch only publishes the four resulting files after every check succeeds.
* A small LethalCatches class owns the per-run last-seen 32-bit hook counter. Take(counter, Vital) ALWAYS advances last-seen, but returns true ONLY if a new lethal catch occurs in Vital::Up or Vital::Off, never during Vital::Down or Vital::Dead.
* TickPartyDeath samples this once every valid game tick, BEFORE the switch which might wake a dead hunter and before TickStanding. The standing branch consumes the already classed tick.caught instead of polling the 0-HP body counter later.
* No global counter reset. Reusing a past count without advancing after respawn never produces a new lethal event; a genuine new post-respawn hit still produces a down. The original game's lamp usage, revive grace, give-up confirmation, map/host authority and game transport are unchanged.
* The original unified-v9/compose_sources.py loads two additional immutable gameplay files that were never modified in V97 (bloodborne_party_death.cpp and bloodborne_re_internal.h), then applies V98 after V97 as one transaction. The result is recorded in the source manifest.

## Validation and remaining gates

* test_patch_upstream_lethal_v98.py tests the original old code's six exact anchors, assures no remaining run.seen_catches in TickStanding, checks the new hook sample precedes any respawn switch, and rejects unexpected sources and a second application.
* test_lethal_catches_v98.cpp runs the actual patched original game's C++ policy: its class definition is **extracted from original pinned bloodborne_party.h**, and its method **extracted from original pinned bloodborne_party.cpp** in CI. These are not hand-written policy copies. Tests Up → Down → Dead (lethal counter advances) → Up (zero queued old lethal hits) → new Up hit (count advances once), and counter reset while dead.
* .github/workflows/shyt-v98-original-game-respawn.yml compiles/runs those exact extracted original C++ blocks with Windows MSVC and Ubuntu GCC and verifies the updated unified source composer.
* V97's Doll local-level-up and V94's pre-auth shadNet oversized-packet fix must still pass the pinned original source gate.

**Not a playable game claim.** The four native C++ integration units have not yet been linked and playtested on two Windows game clients; the old Death/Revive game hook timing, eboot version, save/multi-world transitions and performance under hundreds of players are not yet verified by gameplay QA. Native encrypted Direct P2P gameplay still remains OFF. Do not deploy or merge this draft to Fornex production before testing.
