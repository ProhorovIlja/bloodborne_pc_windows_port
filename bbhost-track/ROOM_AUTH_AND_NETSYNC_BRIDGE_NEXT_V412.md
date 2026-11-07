# BBHost × Yharnam Together: original team-authorization bridge after V412

Date: 2026-11-04. **Engineering contract, not evidence of working seamless co-op.**
Keep playable Draft PR #86 separate from true eboot-free native PR #84.
Original YT reference is pinned at `lKaniel/bloodborne-server@5d2305ee611ef1e03be39ff925f0da75c9a70393` (v1.3.1).
Code and tests in this branch are GPL; never commit original game data, owner credentials or Fornex configuration.

## Verified source boundaries

- YT `emulator/src/core/libraries/network/net_link.h`: SHLK4 `Welcome` proves server **link** acceptance; it does **not** accept a team. `Member` means another peer's link is Quiet, Back or Gone, **not** co-op membership, current map, ownership, slot or P2P permission. `Data` carries a virtual peer address and the P2P frame.
- YT `server/coop/coop_stream.h` + `server/coop/game_link.h`: `Coop` carries a **reliable, ordered, acknowledged stream** of chunked messages, with retransmission/restart and bounded allocation. Do **not** treat a raw Coop datagram as a complete protobuf message. The stream must survive datagram loss and distinguish restart.
- YT `server/coop/coop.proto`: the server's `LobbyState` contains the current team/member list; `TeamStart` carries team id, party key, host, save slot and world; and party `Hello` (`protocol`, `party`, `member`, `run`, `host`, `enemy_owner`) must receive an **accepted party `Welcome`** from the server. `Welcome.epoch` and `Welcome.last` scope world synchronization.
- YT `emulator/src/core/bloodborne_server_world.cpp`: server world progression has its own network thread and `CoopStream`, with a 20 ms cadence. Explicit upstream warning: coupling network work to the game's per-frame update stalled joins. Retain separate queue ownership and prohibit blocking the BBHost main/game thread.
- YT `server/src/bloodborne_world.cpp` and `server/coop/packet_routes.h`: server validates world/party and packet map-owner constraints. YT's session state cannot be reconstructed from a locally invented map or virtual address.
- BBHost `bbhost-track/shyt_bbhost_probe_v1.c`: current NetSync hook is read-only, opt-in, counts channel observations but neither captures nor injects game packets.
- BBHost `bbhost-track/shyt_yt_server_session_v408.cpp`: SHLK4/Noise NK server handshake, cookie, work and heartbeat over actual V406 OS UDP; Data and Coop are quarantined. V412 **parses and queues only MAC-authenticated Link::Member notifications**. Overflow permanently invalidates presence on that session. This is neither team authorization nor gameplay delivery.

## Required integration sequence (do not skip)

1. **Authorized server connection** — retain SHA-pinned YT SHLK4 Noise NK and pinned server key, endpoint identity, anti-replay, asynchronous login Work, heartbeat and reconnect. Disable automatic networking until launcher supplies an explicitly chosen endpoint; never hardcode production credentials.
2. **Real reliable world/team stream** — reuse source-pinned original `CoopStream` + `game_link` with strict receive/held/total-message caps and a network worker separate from `on_frame`. Transport its frames inside encrypted SHLK4 `Coop`, with authenticated ACK/resend/restart and queue backpressure. Do not turn `V408`'s raw quarantine counter into a fake working team stream.
3. **Authorize a specific party/world** — decode original `bbcoop::Envelope` protocol, verify protocol version; accept only server-sourced `LobbyState`, `TeamStart`, and accepted *party* `Welcome` matching local identity and requested team/party/world/run. Track the server's epoch and membership/slots. Any lost session, world load, changed team, peer gone, stale server snapshot, or V412 queue overflow invalidates game-delivery authorization until a fresh authoritative snapshot.
4. **Apply delivery policy** — accept a game packet only from the authenticated server or from a separately authenticated, explicitly approved direct peer. Validate it against the active party, sender ID, slot, current map, enemy-owner/invasion restrictions, packet class and sequence. Preserve `V358` parity with YT server policy; `V362` game-frame format parity is not an authorization oracle.
5. **Bridge to the real game** — first implement bounded per-peer game RX/TX queues with clear lifetime, locking and copy/size limits. Then connect verified NetSync receive/send ABI in BBHost 1.09; never call potentially blocking UDP or protobuf work from the render/game frame callback, never inject during image/world load, and never write to an unverified game image.
6. **Hybrid direct P2P + relay** — direct routing only after server-authorized participant/endpoint identity and key exchange, NAT/STUN validation, per-peer encryption and replay protection; fall back automatically to authenticated server relay on timeout without weakening server authority. Measure Fornex relay bytes/s, loss, CPU and rollback under NAT failures.
7. **Gameplay/release gate** — on two separate real PCs and an isolated server: join during active play; dream/map transitions; late join and crash recovery; invisible actor fix; world/boss/loot sync; save safety; invasions/DBNO; five-person HUD and sessions after vetted upstream #484/#486; p50/p95/p99 performance and reconnect. Only then promote one launcher+BBHost+server+updater installer. `V400` release guard remains closed today.

## Last checked status

- V411 OS UDP spoof-ahead-of-legitimate regression passed Windows/Linux: run `41738181923`; pilot plugin `41738190841` passed.
- V412 added authenticated Link::Member presence events and fail-closed queue overflow, without world authorization. Local original YT responder tests passed Ubuntu/Windows in run `41850926818`; plugin/STUN run `41850941632` also passed.
- Pending full-game work: actual YT co-op reliable world/team state, validated NetSync RX/TX, complete gameplay, five-player UX, hybrid P2P/relay and installer. Not a release.
- **2026-11-04 upstream refresh:** YT #484 five-player changes merged to `main` (NOT published v1.3.1; YT #486 rig remains Draft). YT #506/#507 merged into `release-1.3.2` (not v1.3.1). BBHost #204 merged into `master`, and official BBHost `v0.2.25` was published. The *current playable SHYT baseline* still pins BBHost v0.2.24 and YT v1.3.1; no implicit cherry-pick or tested v0.2.25 migration. The upgrade candidate runs on exact commit `7dbe6f60f33fff45ea1bcbf6c6e61a6b35466e13` in the separate `yt-bbhost-v025-pinned-upgrade-candidate.yml` CI workflow.

**Constraints:** No production Fornex writes, no retail game binaries or user identifiers in public GitHub or CI, no publishing experimental artifacts as complete releases.
