# Seamless Hunt × Yharnam Together: isolated dedicated-server PoC

**Status 2026-10-23: design and offline-tested developer kit only. No confirmed Linux build, online multiplayer, client compatibility, or production deployment.**

## Upstream audited

Repository: https://github.com/lKaniel/bloodborne-server at `77e350743a7cb4524cfcc1782fb6e3af64e25b15`.

- `server/` is C++20, Qt 6, protobuf-based shadNet with Yharnam-specific TeamLobby, server-owned world and UDP game relay.
- `bbport/launcher/bbport_coop.py` constructs UDP/WebAPI/backend endpoints from the host IPv4 and the port constants. Official BLauncher.exe must be **rebuilt** with staging overrides; changing an existing user installation is not adequate.
- The co-op team leader is a game participant, independent from the physical server host. The user's Fornex Linux VPS may be a remote server target if the build and clients prove compatible.
- The original launcher uses local-IP detection to decide whether to spawn a local server. A remote VPS IPv4 should not trigger that condition.
- `server/coop/team_lobby.h` uses `TeamSize=4`, and `team_lobby.cpp` allocates exactly three guest signs `{7,6,5}`. Five hunters require guest slot, NetSync, HUD, spawn, persistence and five-client regression work.
- The existing CLS-compatible shadNet at `play.seamlesshunt.com` is **not** protocol-compatible merely because both projects derive from shadNet. Mixing their databases, binaries, protocol packets or default ports is forbidden.

## Isolation plan

| Server endpoint | Existing production | Yharnam test only |
| --- | ---: | ---: |
| shadNet internal TCP | 31313 | 32313, loopback-only |
| UDP game link | 31314 (different protocol) | 32314 |
| WebAPI TCP | 31315 | 32315 |
| Bloodborne backend TCP | 20443 | 21443 |

New `SHADNET_HOME`, dedicated SQLite and `bloodborne_worlds`; no production state migrated. Default bind 127.0.0.1. For remote multiplayer expose **only** to an approved Tailscale IP/ACL during first tests. No account credentials from legacy servers.

### Client dev override contract

After rebuilding an isolated Yharnam Together test launcher with a small source patch:

```bat
set "SH_YT_TCP_PORT=32313"
set "SH_YT_UDP_PORT=32314"
set "SH_YT_WEBAPI_PORT=32315"
set "SH_YT_BACKEND_PORT=21443"
```

Players enter the reachable **VPS IPv4** on the launcher's Co-op page, not their own PC's LAN address. The currently released launcher lacks these overrides. Do not use an unmodified release and claim the above settings work.

## Proof of concept acceptance gates

1. Pinned upstream shadNet **compiles on Linux** with Qt6 Core/Network/Sql/Concurrent/HttpServer, C++20 and protobuf. Build errors must be fixed in the isolated copy, not on production.
2. Test instance listens on correct isolated UDP/TCP ports; DB, logs and world files isolated.
3. Two identical Windows test builds reach the VPS and sign in with disposable, auto-provisioned identifiers.
4. A game-hosted Team Lobby forms, invites and starts, both players spawn in the same world.
5. Movement, damage, enemy HP, boss/door flags, lamp transitions, down/revive and disconnect/rejoin pass live tests.
6. Shutdown/rollback leaves CLS users and existing Seamless Hunt services unaffected.

**Not in PoC 0:** public quick matchmaking, 5-person teams, PvP invasions, native PC reimplementation without PS4 runtime, legacy CLS cross-client joins.

## Follow-up after successful remote co-op

- `LobbyDirectory`: a versioned public-room list with capacity, region, world/NG+, password/private flag, invitation ACL, modpack and build compatibility.
- `QuickJoin`: server-side atomically reserved slots with expiry to prevent overbooking and unintended party mixing.
- `PvP`: explicit per-room invasion opt-in; guests cannot bypass session access controls.
- Fifth hunter: only after multi-client gameplay tests confirm fourth guest slot in the game code, not just a C++ constant.
- Separate protocol adapter to CLS, if technically feasible and permitted by collaborating developers.

## Reproducible developer toolkit

A tested local ZIP named `SH-Yharnam-Together-POC-20261023.zip` was produced in the development session. It includes:

- `build_linux.sh`: source-pinned isolated CMake build and 2 upstream server unit-test targets.
- `prepare_staging.py`: dedicated config/state/binary staging, default loopback, port validation and strict non-overwrite behavior.
- `patch_launcher_ports.py`: reversible *source-only* four-port client override.
- `tests/test_poc.py`: 7 offline tests of isolation, source pinning, port overrides and backup/restore.
- `README-RU.md`: step-by-step non-production commands and safe acceptance criteria.

The toolkit is not an executable server or gameplay-tested client. It deliberately includes no retail game data or account secrets. The production deployment is out of scope until separate approval.
