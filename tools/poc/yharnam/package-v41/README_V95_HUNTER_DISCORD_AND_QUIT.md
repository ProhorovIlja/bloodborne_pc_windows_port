# V95: real Blood Level / stat-build identity and in-game Quit to Desktop

Scope: **native Yharnam Together Windows GPU client, source-only DRAFT PR #20**. This change does NOT use or require shadPS4 to play the game, does not touch Fornex production, and does not claim to publish a Rich Presence status to Discord yet.

## Grounded in the game's own character memory

Original pinned `bbport/gpu/shim/bbport_save_editor.cpp/.h` already expose `BbSaveEditor::Read()`, which validates an in-world character and reads **actual** PlayerGameData level +0x90 and attributes VIT +0x40, END +0x48, STR +0x58, SKL +0x60, BLT +0x68, ARC +0x70. There is no guesswork from character name or an untrusted multiplayer peer. It re-reads live values, including level-ups/respecs.

Added `sh_hunter_presence_v95.hpp`: a small C++20-compatible pure formatter. Valid level range 1–544, six attributes 1–99; invalid/incomplete saves produce no published identity. Blood Level uses exact in-game `c.level`, **not** a guessed value derived from stat sums.

The requested minimum for a weapon-scaling build attribute is **18** inclusive, applied ONLY to Strength, Skill, Bloodtinge and Arcane. Vitality and Endurance are survival characteristics and do not create a fake offensive build label. Classification: no offensive stat at 18 → `Developing Hunter`; exactly one → `Strength`, `Skill`, `Bloodtinge` or `Arcane`; STR+SKL → `Quality`; exactly two others → e.g. `Skill/Arcane`; three or four → `Hybrid`. This is a **heuristic based on stats**, not a guarantee of equipped weapon, gems or PvE/PvP intent. Can be refined in future from validated weapon data.

Example local activity details: `BL 120 | Skill/Arcane`. Optional `Options{show_level, show_build}` support separate privacy switches. It does not contain account identifiers, usernames, IP addresses, passwords, world secret, Discord join secret or peer private candidates.

## Real in-game interface changes

`patch_bbport_hunter_presence_v95.py` strictly patches the pinned original native renderer source `bbport/gpu/shim/bbport_overlay.cpp` and stages the classifier header **before native GPU build**:
- The game's own Save/character menu displays a real read-only BL/build **Discord preview (local only)**. The underlying character editor and save are not modified.
- The original Game System → Co-op Team screen, when opened **while playing**, now gets a direct **Quit to Desktop** fourth menu button next to Close. Selecting it simply closes the Team menu and opens the existing native `QuitBox` confirmation dialog. The original settings menu already contains Quit and L3+R3 hold shortcut; these are preserved.
- The existing Quit dialog defaults to Cancel, warns about any unsaved progress and ultimately posts `SDL_EVENT_QUIT` for the original window shutdown path. No `std::exit`, `TerminateProcess` or forced game kill.
- Unrelated 3-button title team screen layout and normal game co-op/relay are preserved.

## Validation and remaining gates

- `test_hunter_presence_v95.cpp`: Windows MSVC + Linux GCC, exact 18 threshold, all offensive builds, Quality and hybrid, invalid ranges and privacy.
- `test_patch_hunter_presence_v95.py`: pinned source insertion, fail-closed source drift, original safe Quit path reuse and no fabricated Discord activity.
- `.github/workflows/shyt-v95-hunter-bl-discord-preview.yml`: tests on Windows and Ubuntu, checks the **actual pinned original** game overlay.
- The full native Windows build workflow `shyt-v36-composed-windows-client.yml` now stages V95 into original native game code before renderer compilation. **Until full game link/package CI and two-PC runtime succeed, this is not a playable/tested release.**

**Discord transport not yet wired.** The current public CLS BBSC and pinned Yharnam Together fork sources still expose legacy shadPS4 Discord RPC code and do not prove that the user's Discord screenshot join/banners are in their public game runtime. V95 is the game-owned trustworthy value provider and on-screen preview; the next task is an **opt-in, rate-limited native Discord Rich Presence bridge** using an explicitly configured Discord application identity. Preserve existing legitimate party size/area/invite fields if present and never overwrite or leak secrets. A game save should not silently enable sharing BL/build.
