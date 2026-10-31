# V158 + V159: actual original Qt game-receiver and lobby-refusal evidence

**Original Qt/Redis/shadNet 200-player hosted runner, five-hunter teams, unchanged QoS requirements.** [CI #41097996435](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41097996435) completed **SUCCESS ONLY AS A DIAGNOSTIC WORKFLOW**, with five real loadtest scenarios. GitHub Actions evidence artifact **12996674466**, `yt130-V157-200-player-real-Qt-loadgen-4-8-16-worker-A-B-DIAGNOSTIC`. Pinned original YT1.3 source SHA `0645740a33ae21c56df3b4a0d9777086dbca6053`.

All 5 run scenarios have **zero**:
- Qt `QUdpSocket::readDatagram` errors and short reads from bbload's real client UDP sockets.
- `ServerLink::DecodeData` failures after authentication.
- SHAD game-frame bad headers, game-frame decode failures or malformed short embedded game entries.

All observed kind3 Data datagrams that reached original Qt bbload were accepted and decoded into valid game frames; game-entry delivery gaps remain. This is strong evidence against malformed Data/SHAD encoding being the primary cause in this **local synthetic hosted workload**. It is **NOT** a proof there was no UDP loss before the receiver, and does not prove any live player/NAT performance.

| Real Qt 200-player case | Playing / teams | Steady game-entry ratio | Server kind3 sampled UDP in=out | Qt client game Data frames successfully decoded | Qt TeamLobby refusal 'other' breakdown |
|---|---|---:|---:|---:|---|
| 1 shard, 5 owners, 4 bbload processes | 200/40 | **84.90%** | 611,220=611,220 | 683,220 | no other notice |
| 1 shard, 5 owners, 8 processes | 200/40 | **82.81%** | 655,208=655,208 | 703,208 | no other notice |
| 1 shard, 5 owners, 16 processes | 200/40 | **88.15%** | 525,864=525,864 | 590,647 | 64 'already joined', 32 unknown other |
| 3 shards, code join, 1 owner, 4 processes | 200/40 | **96.93%** | 228,220=228,220 | 240,124 | 8 'team full' replies |
| 3 shards, code join, 1 owner, 16 processes | **175/35**, 25 in Lobby | **96.92% raw; min steady window 0ms, not valid** | 202,376=202,376 | 214,404 | 30 'already joined', 4 unknown other |

Numbers are per-run totals with different scopes:
- Qt LinkServer original `YT130_WIRE_TRAFFIC kind=3` is sampled 5-second **server** ingress/outgoing write datagram counts, excluding partial tail.
- Qt bbload V158 `game_frame_decoded` counts authenticated, successful **client receive** calls across the entire run, including possible receives in partial tail windows. Therefore client counts exceeding server sampled totals **do not prove packet creation or duplication**. Their windows are not synchronized.
- Game `packets_sent` and `packets_received` count **embedded game entries**, not raw Data datagrams.
- The counts `team_already_joined`, `team_full`, etc. are **server replies** observed by test clients, not unique affected people or causes. Example: 30 'already joined' replies do not mean 30 different members were rejected.

The actual original `Game::Tick` source retries cross-shard `JOIN_CODE` while its own last `LobbyState` has not acknowledged membership; `team_id.empty()` and join backoff control repeated requests. An 'already joined' response may therefore be an **idempotency/ack lag artifact**, not necessarily why 25 clients never reached Playing. Original C++ uses `team_members` and `started` to decide who can START. Do not blindly disable JOIN_CODE retries, alter world ownership, or lift lobby security limits.

## Next validated questions (do not claim fixed)

1. **Client receive socket queue:** collect per-process, per-socket `SO_RXQ_OVFL` or equivalent alongside event-loop scheduling. Qt `readDatagram` validates received packets but cannot count those discarded in the kernel **before** that call. Previous host-wide Linux `Udp RcvbufErrors=0` is not equivalent to per-socket overflow evidence.
2. **Synchronize sampling windows:** compare sender-queued Data **datagrams** vs successful Qt server sends vs client received Data datagrams in a matched time interval, not 5-second sample vs whole-run totals, and not game-entry vs datagram counts. Count first/last per-client gameplay frame and sequence offset without logging identities or payload.
3. **Lobby state acknowledgements:** trace anonymous per-team readiness counters and leader START timing (not private names or codes), reconcile repeated `JOIN_CODE` with delayed `LobbyState.team`, especially 3-shard/16 bbload processes.
4. **Real game release gate:** Windows game, 5-player gameplay, real WAN/NAT/ICE encrypted Direct P2P, CPU/latency, and 200 independent players require hardware-backed tests. A passing diagnostic GitHub job cannot satisfy this.

**All five tested configurations remain under the 99% minimum game-entry quality requirement or lacked all 200 Playing. No public release, Fornex deployment, or protocol switch is authorized.**
