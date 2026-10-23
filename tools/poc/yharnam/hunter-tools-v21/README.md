# V21 Hunter Tools and safe co-op defaults

Pinned upstream: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`.
Development branch: `feature/yharnam-dedicated-server-poc`.

## UI design

The old **Save** settings page mixed character mutation into general settings, while five gameplay cheats were mixed into **Game effects**. V21 renames that page to **Hunter Tools** / **Инструменты** and brings together:
- Character editor: Blood Echoes, Insight, six attributes, goods, weapons, armor.
- Gameplay cheats: no death, stealth, silent footsteps, no Rally decay, enemy control.

The general Game effects tab now excludes `cheat_*` options. Normal graphics and gameplay tweaks remain in their previous location, with all save editor features retained.

Hunter Tools starts locked every game launch and when the image is reset, and needs an explicit **Unlock for this session** while a character is loaded. The unlock is never persisted. Online or lobby play blocks the tools.

The in-game `BbSaveEditor` functions are guarded **at enqueue and dispatch time**. A reconnect between clicks and execution discards pending mutations. Stat retries also re-check permission. Invalid item categories and quantities outside 1–99, and null attributes arrays, are rejected before calling the game. The integer calculation of changed character level now uses int64 and clamps the final level to Bloodborne's 1–544 range. That prevents signed integer overflow from damaged character data.

## Online/co-op detection

A native C bridge `bbcoop_offline_character_edit_allowed()` checks all of:
- `!Coop::TeamModeOn()`
- `!Coop::InPartySession()`
- `Coop::SessionMembers() <= 1`
- `Coop::SessionPlayers() <= 1`

This covers normal Team Lobby and many legacy/ordinary co-op sessions, and fails closed while Team Mode is enabled, even during connection. These are local client checks, **not real anti-cheat or authorization by a server**.

## Why no fake "Host allows cheats" switch?

Offline save editing directly modifies the character's local memory. The host cannot reliably stop a user who modifies their binary or bypasses a client guard. A trustworthy host permission feature requires an agreed protocol, host-signed party rules, compatibility negotiation, enforceable server-owned actions, and a default deny for mismatched peers. Character stat changes and game patch cheats are not safely enforceable by simply adding a checkbox to the lobby. V21 deliberately avoids such a misleading switch.

**Caution:** a game patch cheat already enabled at process startup may remain active until game restart; moving its setting in the UI is not a live patch revert. Before returning to public sessions, restart with the cheats disabled. Private-lobby permission may be an option in a future dedicated protocol, but not with unauthenticated legacy clients.

## Validation

- Conservative UI/editor/co-op C bridge source transforms in `patch_hunter_tools.py` fail when upstream anchors change.
- `test_patch_hunter_tools.py`: source mutation/guard/overflow-safety tests.
- `sh_hunter_tools_policy.hpp`, `test_hunter_tools_policy.cpp`: portable C++20 permission and overflow tests.
- `unified-v9/compose_sources.py`: integration after V20, preserving V3–V20 changes and existing cooperative bridge edits.
- Local policy-equivalent C++20 fixture compiled with -Werror and UBSan and passed.
- Full Windows Bloodborne build, multiplayer runtime, complete GitHub Actions suite not yet verified.

No changes were made to the live production CLS/Fornex host.
