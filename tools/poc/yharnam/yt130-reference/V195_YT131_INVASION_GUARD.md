# V195: YT 1.3.1 source-locked five-body / single-invader admission

The official Yharnam Together v1.3.1 `server/coop/invasions.h` still enforces `InvasionMaxPlayers=4` and its original Qt `Service::JoinInvasion` can alter the invader's session/hostile routing **after** a 10-second notice, without rechecking that the fifth co-op guest hasn't just taken its slot. V194's five-seat TeamLobby alone cannot prevent this disagreement.

This extension stays in [existing Draft PR #75](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/75); it is **not** an independent gameplay release.

## Source-checked implementation

`stage_yt131_invasion_guard_v195.py` runs **after** source-locked V194 against the exact public upstream release `5d2305ee611ef1e03be39ff925f0da75c9a70393`. It verifies the original blob SHAs for three previously-unmodified upstream C++ files and rejects modified originals, a missing V194 five-seat TeamLobby, changed anchors, repeated application, or unexpected Git head.

It modifies only `server/coop/invasions.h`, `server/src/bloodborne_world.cpp`, `server/tests/test_invasions.cpp`. The upstream protobuf and friend/session auth service are untouched.

- Adds a **five-total-participant** role contract, with explicit `ImplementedInvadersPerWorld = 1` until actual multiple-invader and game hostile-kind/sign parity exist.
- The matchmaking target counts **reservations from all team members** as well as currently connected co-op actors, so a loading/disconnected fifth co-operator does not leave a falsely free seat.
- Delayed `JoinInvasion` rechecks that the team/session exists, host still allows invasions, no boss fight is running, the co-op + hostile fit in the five seats, and a genuine guest sign `4..7` is available **before** changing hostile state or routing.
- On a later team change that fills all five co-op slots, actively ends any conflicting invasion instead of allowing five cooperators and a hostile to persist together.
- Extends the **actual original** `test_invasions.cpp` with `FifthSeatInvaderCapacityAndOptIn` for 4+1 accepted, 5+1 rejected, host opt-out and closed session rejected. Keeps `3+2`, `2+3` as a design contract only, **not** supported by this single-hostile service.

## CI and proof boundaries

- `test_yt131_invasion_guard_v195.py` has synthetic fail-closed source contract tests.
- `.github/workflows/shyt-v195-yt131-invasion.yml` checks original HEAD, stages V194 then V195 in a disposable checkout, verifies exactly six changed files and an untouched protobuf, then compiles/runs original `test_team_lobby` and `test_invasions` with real Qt6 and pinned upstream protobuf.
- [CI run 41250609797](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41250609797): original source-stage job **SUCCESS**, C++ compile/CTest result must be read independently when complete.

**No proof yet:** retail game hostile phantom kind/sign values (upstream `InvasionKind`/`InvasionSign` remain experimental placeholders); simultaneous two/three invader ledger, secure real Direct P2P, authentic five-body game rendering/network replication, remote multiplayer gameplay, resilient 200-player server transport, full standalone Win64-native Bloodborne source-port or Fornex deployment.

Opt-in invasions remain disabled by default; no real game/server or user saves are changed. Never merge/deploy this until those gaps are separately verified, and never publish user game binaries or derived private code.
