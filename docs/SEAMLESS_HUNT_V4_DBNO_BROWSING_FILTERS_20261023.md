# Seamless Hunt V4: DBNO host setting, in-game lobby browsing and Quick Play filters

Date: 2026-10-23. Design response to CLS request that Down But Not Out (hit-to-revive) be a host-selectable mechanic, visible to prospective session joiners.

## Existing underlying sources

Pinned Yharnam Together lKaniel/bloodborne-server at 77e350743a7cb4524cfcc1782fb6e3af64e25b15. In-game menu in bbport/gpu/shim/bbport_overlay.cpp Team::Screen, matchmaking in server/coop/team_lobby.cpp, DBNO gameplay in emulator/src/core/bloodborne_party_death.cpp, party status in server/src/bloodborne_party_boards.cpp. Host game currently supports 4 team members, not 5; do not advertise more.

## New C++ model in the working branch

tools/poc/yharnam/ingame-online/session_matchmaking.hpp now includes:
- Rules.dbno_enabled (default true, matching current YT DBNO behavior).
- Room title, region, started, rules_revision, and RoomView containing public gameplay settings without exposing passwords, account secrets or tokens.
- RoomFilters: optional DBNO and invasions booleans (Any/On/Off), scaling preset, P2P preference, region, hide_full/min_free_slots, include_started.
- Browse (filtered public room cards) and QuickPlay using the same filter predicate, with full-game-build check and server-side capacity reservation.
- Configure (host identity + expected rules_revision), only before hunt starts, with pending slot reservations invalidated on rules update. StartHunt freezes rules during a hunt.
- Passworded/private rooms are never discoverable in public listings or Quick Play. Invasions into such sessions are forbidden even when the attacker has private-room access.

C++ test test_dbno_browser.cpp covers DBNO filters, Quick Play, host-only config, stale revisions, started-game lock, full-room read-only listing, protected private rooms. Add to CMake tests and the existing offline workflow.

## Standalone local HTTP PoC V4

Released as conversation ZIP SH-YT-DBNO-LOBBY-FILTERS-V4-20261023.zip, not deployed. Python matchmaking.py+matchmaking_http.py: GET /v1/rooms accepts dbno=any|on|off, invasion=any|on|off, scaling, hide_full, min_open_slots, include_started, region and Blood Level; POST /v1/quickplay accepts identical filters in JSON; host-signed /configure accepts down_but_not_out with expected_revision. All public room cards return down_but_not_out, scaling, invasions_enabled, free_slots and revision. Tested: 31 Python unittest cases + 5 C++ CTest executables all green (local package), including DBNO-off combat transitions and reservation invalidation on settings update.

**These are prototypes**, NOT integrated into Fornex shadNet's authenticated Qt WebAPI, original co-op protobuf, native in-game UI or combat hooks. The local HTTP service binds only 127.0.0.1:32316 and must not be made public. No VPS services, production CLS, firewall, or DNS touched. GitHub CI run not confirmed.

## Actual game semantics required

1. In-game Co-op Team -> Session Settings: host may toggle DBNO On/Off, invasion On/Off, scaling; these changes must be sent through authenticated game-to-shadNet protocol, not an untrusted host_id supplied by arbitrary HTTP clients.
2. Server persists rules and distributes authoritative revision to every connected participant. If session is active, reject rule changes until next session so participants cannot disagree about down vs death.
3. DBNO On: when a player goes down, a standing member of the *same party* can revive by verified game attacks. Defenders must never revive invaders and vice versa; for attacking parties, all down/gone -> return attackers to their own world, not disconnect accounts. Existing YT revive damage rule scales 1x, 2x, 4x by downs.
4. DBNO Off: a lethal blow follows normal game death without the Down state or hit-to-revive. Implement this in actual TickPartyDeath and both sides' game hooks, not just the JSON setting.
5. Browser: show current rule flags, Blood Level bracket, game version, group slots and actual network route quality. Quick Play must use same matching filters and atomic party reservations; showing full rooms doesn't make them joinable.
6. Continue using P2P for high-frequency SHLK game packets after trusted UDP negotiation, with relay fallback; control/world remains on Fornex. This V4 does NOT provide actual P2P networking or CPU savings.

Default lobby rule should preserve current DBNO when host doesn't change it. No player should manually enter the Seamless Hunt server address or set up a VPN.

Before publishing a player-facing download, build a matched native Windows BBPort runtime and Qt server from the same pinned revision, connect the actual game menu to real authentication and live rule messages, and run multi-client join/death/invasion tests.
