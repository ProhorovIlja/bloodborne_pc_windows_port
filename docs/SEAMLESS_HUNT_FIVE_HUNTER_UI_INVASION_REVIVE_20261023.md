# Seamless Hunt: adaptive five-hunter UI and party-versus-party invasions (2026-10-23)

## Verified upstream, pinned `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`

- Native in-game menu: `bbport/gpu/shim/bbport_overlay.cpp`, `Team::Screen`. Source renders four 290×270 cards using gold/stone art. Cards are drawn with `Card()`, and list HUD with `Party::` code. The current lobby displays `of 4`.
- Four-player runtime boundaries are deeper than the UI: `server/coop/team_lobby.h` has `TeamSize=4`; `team_lobby.cpp` assigns guest signs 7,6,5; `bbport/gpu/bbcoop.h` has `BBCOOP_LOBBY_TEAM=4` and `bbcoop_team_load.rows[4]` and HUD arrays. Do not change capacities until game guest slots, native world replication and bridge are updated and tested.
- Existing revival: `emulator/src/core/bloodborne_party_death.cpp`, `emulator/tests/bloodborne/test_bloodborne_party_death.cpp` calculate healing by melee damage, first/second/third down requires 1x/2x/4x target max HP. Currently only allied co-op, no verified PvP invader roles.
- Current UDP `server/src/link_server.cpp` forwards game SHLK Data via Fornex. Direct P2P with authenticated rendezvous/relay fallback is still future integration and a separate workstream.

## User-approved UI rules

- The in-game `System > Co-op Team` screen must contain Quick Play, browser, private invitations, host settings and invasion controls. Desktop launcher stays installation, graphics, mods, patching and diagnostics only; server address defaults to Seamless Hunt without typing it.
- Five slots should appear **in a single row**, by scaling entire cards, icons and font glyphs as a unit. The current four-card baseline is `4×290 + 3×24 = 1232` logical px. Five at `5×290 + 4×24 = 1546` are displayed at `1232/1546 ≈ 0.797` of the baseline. For narrow displays, preserve minimum readable size and offer horizontal scrolling rather than hiding names or adding a second row.
- HUD: preserve the original Bloodborne health-bar artwork, but show explicit textual/badge roles HOST, ALLY, INVADER in the game's chosen language and tone. Invader is not merely a color; role MUST come from server-authorized participant metadata. Scale four remote health bars to fit the three-row baseline when five total players are present. Draw a visible revival-progress meter only for compatible downed teammate.
- Host may opt into invasion in PUBLIC, passwordless rooms. Passworded or private rooms must never be picked for invasions, even if `allow_invasions` is toggled. Quick Play hides passworded rooms.
- Attacker team may contain two friends. In an eligible five-slot world with three defenders, both arrive as an atomic two-person reservation. A defender strike cannot heal a downed attacker; only a currently standing member of the same invader party can revive them via verified combat hits. If all attackers are down/gone, terminate **only** the invasion visit and return every attacker to their own saved world; do not log out or wipe the defending world. Defender revival is limited to its own defending party.
- Keep all in-game UI input accessible via gamepad, keyboard and mouse. Configure UI scale inside the game once settings persistence is wired; a fixed 1.0 user-scale placeholder in a source patch is not yet a player option.

## Implemented and locally checked in conversation artifact

Development ZIP: `SH-YT-INGAME-UI-PVP-V2-20261023.zip` (provided in chat):
- `session_matchmaking.hpp` existing portable in-game C++ policy, newly made password-protected rooms invasion-immune (matching change also committed directly to this branch, `c52751e3a2fef66164baf1883a4c666c9fd45147`).
- `hud_layout.hpp`: auto-fit 4/5 cards and four remote bars; role/name text with color as supplemental cue.
- `invasion_lifecycle.hpp`: future game-authoritative invader Down / revived-by-same-party / all-down -> ReturnToHome events, per-hit ID replay resistance, revive damage threshold 1x/2x/4x.
- `PATCH-YHARNAM-TEAM-UI.py`: fail-closed developer-only source transformer of the original `Team::Screen` section. Creates a separate `bbport_overlay.cpp` with transformed vertices (including text/art) and `sh_yharnam_layout.hpp`, does not modify original game/production; only has four cards until authoritative runtime model expands.
- `test_ui_invasion.cpp`, `test_session_matchmaking.cpp`, `CMakeLists.txt`: GCC14 C++20 Release build, 2/2 CTest PASS locally. Transform smoke on pinned-source excerpt and rerun protection PASS.

**IMPORTANT**: ZIP is not yet installed on Fornex, not connected to game UI or native game events, not an executable player update and not proof that PvP, revival or fifth player works in Bloodborne. Next direct development is client/server authorization and real in-game UI integration followed by five-slot protocol and direct P2P load tests. Preserve all running Seamless Hunt / CLS ports/services until verified candidate is ready.
