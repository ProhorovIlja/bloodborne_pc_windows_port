# V5 native DBNO wiring, pinned source (2026-10-23)

## Implemented source-path scope

Developer source generator: tools/poc/yharnam/native-dbno-v5/APPLY-NATIVE-DBNO.py

Pinned source: lKaniel/bloodborne-server at commit 77e350743a7cb4524cfcc1782fb6e3af64e25b15. Inspected GitHub source: 14/14 patch anchors were found uniquely in eight native source files.

The isolated generator updates:
1. server/coop/coop.proto: protocol 7 -> 8; TeamRequest SET_DBNO=12; boolean request payload; optional team rule, missing rule means legacy ON.
2. server/coop/team_lobby.cpp: create teams with DBNO ON; server-authenticated leader alone changes it before Start, server sends updated LobbyState after a successful change.
3. emulator/src/core/bloodborne_re_internal.h and emulator/src/core/bloodborne_server_world.cpp: game sends TeamSetDbno over existing reliable Coop stream, and TeamDbnoEnabled reads the received team state.
4. bbport/gpu/bbcoop.h and bbport/gpu/bbcoop/coop.cpp: extend existing native C ABI bridge to expose DBNO status and toggle command.
5. bbport/gpu/shim/bbport_overlay.cpp: add a mouse/controller/keyboard button in the existing in-game Team menu, disabled for guests and after the hunt starts.
6. emulator/src/core/bloodborne_party_death.cpp: TickPartyDeath reads the server rule. OFF clears interception flags and emits ordinary Vitals; ON keeps existing hit-to-revive behavior.

Local package SH-YT-NATIVE-DBNO-ENDTOEND-V5-20261023.zip contains an equivalent source patcher, source-fragment tests and Russian instructions. 3/3 local unittest cases passed for eight transformations, atomic failure, no in-place modifications. These are NOT a compiled native game or live co-op test.

GitHub workflow .github/workflows/yt-native-dbno-v5.yml retrieves the real pinned upstream tree, patches eight files and attempts protoc schema generation, then uploads the generated source bundle. CI completion has not yet been observed.

## Protocol and safety

Protocol 8 is intentionally incompatible with the running protocol-7 Yharnam PoC on Fornex. Do not update or merge binaries piecemeal. Native Windows BBPort and Qt shadNet must be rebuilt as a matched pair; test reconnects, deaths, down transitions, save integrity and all client-side UI controls with two actual machines.

This patch is NOT full five-player gameplay, group invasions or Direct P2P. V4 Quick Play/filter models are not yet connected to this real protobuf lobby. Full PvP role separation, DBNO revive-only-own-party, return-home, and real P2P need further game/server implementation.

CLS production services, experimental Fornex instance, DNS, firewall, player save data and installed Windows files were not touched. Keep this a development-only source patch. End users should eventually receive a one-click installer with automatic Seamless Hunt endpoint and in-game options, without manual Python/Git/VPN.
