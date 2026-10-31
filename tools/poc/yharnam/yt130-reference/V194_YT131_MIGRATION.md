# V194: Yharnam Together v1.3.1 five-seat source migration

**Status: original v1.3.1 source gate passed; actual Qt C++ execution is a separate CI gate.** This file is a source-checked handoff and does **not** assert playable five-user co-op, successful P2P or production deployment.

## Verified upstream comparison

- Original project: `lKaniel/bloodborne-server`.
- Existing supported research pin / last V184 server stack: `0645740a33ae21c56df3b4a0d9777086dbca6053` (v1.3.0).
- Published official v1.3.1 release target: `5d2305ee611ef1e03be39ff925f0da75c9a70393`, released October 31, 2026.
- GitHub compare: **107 ahead, 0 behind, 172 changed files**. Among others, changed `server/coop/team_lobby.{h,cpp}`, `server/tests/test_team_lobby.cpp`, `server/coop/coop.proto`, `server/src/bloodborne_world.cpp`, `server/src/{database,link_server}.cpp`, `emulator/src/core/bloodborne_team.cpp`, and UI/launcher sources.
- `coop.proto` still declares `PROTOCOL_CURRENT=8`, **but** adds `FRIEND_ADD=19`, `FRIEND_REMOVE=20`, `FRIEND_DECLINE=21`, `SEARCH=22`, `OPEN=23`, `ASK_JOIN=24`, `ASK_CANCEL=25`, `ASK_ACCEPT=26`, `ASK_DECLINE=27`, `RESET_LAMPS=28`, `Team.join=12`, `LobbyState.friends=7`, `open_teams=12`, `team_size=14`. Do **not** infer runtime interoperability from the identical protocol number. Release compatibility also depends on the exact client/server build and auth semantics.
- Official `TeamSize=4` and `GuestSigns={7,6,5}` were unchanged on these source anchors. Game `TeamGuestSign` uses the server assigned sign if present, and otherwise computes signs from 7 by guest rank. **Game's actual fourth remote character and original native packet handling need multi-PC proof.**

## Implemented in existing Draft PR #75, not a fresh feature branch

- `stage_yt131_five_seat_v194.py` requires **exact v1.3.1 git HEAD** plus exact original 4 Git blob SHAs (including protobuf). Any drift, missing field, source mismatch, already-applied patch or invalid old anchor causes failure before writing any of the 3 modified files.
- Reuses the previous source-checked `patch_five_hunter_team.py` five-slot server TeamLobby patch. Updates official `TeamSize` to five, changes guest signs to `7,6,5,4`, adapts previous server test expectations and preserves new 1.3.1 protocol and friends/open teams.
- Adapts **official** new `OpenTeamsAreAskedToJoin` test: 4-player ASK team remains visible, fifth asks and is admitted, sixth is refused, leaving frees the slot. Adds real original Qt `FiveSeatPublicOpenTeamHonorsServerCapacity` C++ test: fifth OPEN join, sign 4, sixth refused, sign reuse.
- `test_stage_yt131_five_seat_v194.py` provides synthetic fail-closed source gating tests, including wrong checkout. Tests do not contain any retail game files.
- `.github/workflows/shyt-v194-yt131-five-seat.yml` (pinned source, read-only checkout, bounded output): stage source and unit tests, then compile and execute original Qt `team_lobby` + `bloodborne_world` tests on the release source with exact protobuf submodule. No changes to user server.
- Last original **source-gate SUCCESS**: [V194 Actions](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41250084912) at exact `b2b79e9`/subsequent head; Qt outcome must be checked separately on completed job. Failed initial CI attempts were test harness/bash issues, not considered game proof.

## Known blockers before a true five-user YT1.3.1 client/server stack

1. Original v1.3.1 `server/coop/invasions.h` still has `InvasionMaxPlayers=4`. Our previous v1.3.0 five-seat guards/multi-invader ledger (PRs #72/#75 predecessor scripts), DBNO/HUD persistence and hostile slot verification **must be re-reviewed against changed v1.3.1 world code**. Do not apply old source-pinned stage scripts blindly. Verify 5+0, 4+1, 3+2, 2+3 (total five), and explicit host invader OFF.
2. The actual YT v1.3.1 multiplayer game/client hooks and UI, game save/world semantics, 4th remote sign, session traffic, boss/chalice synchronization and host-transfer failover must be rebuilt and **played on multiple real PCs**. A TeamLobby CTest does not prove five simultaneous game characters.
3. Original v1.3.1 native invader guest race (#475) remains a **draft**, while our own PR #73 already has V177 source-checked improvement against v1.3.0: don’t duplicate it; forward-port and test the real room membership semantics + invalidation on changed invader identity.
4. v1.3.1 includes new friends/OpenTeam/ASK and SQLite-backed friend storage; preserve the authoritative auth/privacy boundaries and avoid making open parties passwordless on the public Internet or unintentionally altering saved world ownership.
5. Verify network two-plane design: server for identity/discovery/control; direct encrypted peer streams when reachable, secure bounded fallback otherwise. Current 200-player latency/delivery evidence is not sufficient for a production hybrid claim (P2P still unproven).
6. Migrate experimental `LobbyLimits` only on source-locked old-to-new C++ API after proving it doesn't enable unrelated Hosted auth/policy/world features; OFF by default and no breaking current Fornex.
7. Maintain separate native **game** Windows source-port effort (#84 V193). This server-side YT source migration does not independently eliminate PS4 HLE/eboot dependencies in the shipping gameplay client.

## Change and release safety

- All edits occur in an **ephemeral CI clone**; exact protobuf remains byte-for-byte unchanged. The real server, Fornex, master branch, private user archives, saves and account data are not modified.
- No silent merge. Preserve Draft PR chain until native server/game client binaries, multi-PC tests, five-seat role matrix and signed security review complete.
- Upstream research index: Draft [PR #25 SOURCE_RADAR_2026-11-01.md](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/blob/feature/yt130-crossfork-integration-watch-20261027/tools/poc/yharnam/upstream-watch/SOURCE_RADAR_2026-11-01.md).
