# V97: prevent the Doll's Level Up from breaking after co-op joins

**Source-only original native Yharnam Together game fix**, ported from original author [lKaniel PR #407](https://github.com/lKaniel/bloodborne-server/pull/407). This is NOT a new renderer, server protocol, client account system or alternate port. Live Fornex, master, player saves and account databases remain untouched.

## Root cause verified in pinned source

Our original pinned upstream commit `77e350743a7cb4524cfcc1782fb6e3af64e25b15` still classifies unknown event flags as Host + carries home. The Doll uses `6700` as her local "level-up menu open" conversation latch. Upstream's October 25, 2026 playtest found the team's stored world sometimes contained the **host's** 6700 set; applying the team world to a guest permanently prevented the Doll's Level Up choice opening that guest's upgrade menu.

## V97 implementation

The pinned source's actual `emulator/src/core/bloodborne_flags.h` has **a different original `FirstRows` layout** than latest upstream. `patch_upstream_doll_flag_v97.py` exact-matches the original older entry adjacent to the 6680–6697 weapon flags, then inserts the rule `Range(6700,6700,FlagOwner::PerPlayer,0,...)`: no carrying to another world, no host-owned state, no online broadcast and no save from another character.

In `emulator/src/core/bloodborne_party.h/.cpp`, adds `constexpr DollLevelUpFlag=6700` and a tiny `ClearsDollLevelUpFlag(party_configured,flag_on)` predicate, returning false outside a party. In `emulator/src/core/bloodborne_flags_store.cpp`, the exact original `SetGuestPickupsBeforeMapItems` now calls `ClearStuckDollLevelUpFlag` after applying the team world and the lamp requests: if a stale 6700 persists **at map load** while a party is configured, clears it using the original already-known `PartyGhostSetEventFlagOffset`. It deliberately does **not** clear the flag continuously during the Doll's live interaction and has no action when solo.

The original `unified-v9/compose_sources.py` now stages and verifies these four previously unmodified **full native game source files** from the immutable pinned checkout before applying the upstream V97 patch, and records them in the manifest. The source patch is a four-file transaction with exact version anchors, refusing double apply or changed vendor text. No changes to server game-wire format, native UDP P2P transport, FSR or character memory layout.

## Tests and acceptance

- `test_patch_upstream_doll_v97.py`: Python exact old source anchors, all-or-nothing, no duplicate, per-player no-share rule, solo is never cleared, clear happens after team map state is loaded.
- `test_bloodborne_doll_v97.cpp`: **actual original patched C++ flag table** (not a copied rule): `static_assert` that 6700 is PerPlayer with zero behaviours; adjacent weapon/session flags unchanged, 6701 remains host-owned, 6700 is not shared/carries home.
- `.github/workflows/shyt-v97-original-game-doll-levelup.yml`: fetch exact four immutable GitHub source files, apply V97, verify that original composed source includes the fix, compile actual pinned flag header on Windows MSVC and Ubuntu GCC, and reject missing/suspicious anchors.
- Unified original Qt server/game source composer CI: unrelated regressions should stay green.

**Still required:** real native Windows game binary, two-player test: team joins with host 6700 on, both players load Hunter's Dream and open Doll Level Up successfully; ensure quitting, changing map, returning solo and autosave don't clobber upgrades. This patch is not deployed and does not claim to repair user saves retroactively when other saved flags have been corrupted.
