# V155 original Qt shard load: observed game-wire and 200-player QoS evidence

**Evidence:** [real Qt/Redis/shadNet GitHub Actions run #41089608031](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41089608031), original pinned YT1.3 server SHA `0645740a33ae21c56df3b4a0d9777086dbca6053`, V155 head `f0daef4db3983c07c368126e8df331eb7d9dd59a`, artifact ID **12994826931**, name `yt130-V155-5-seat-200-player-owner-and-shard-evidence-NOT-RELEASE`.

**Outcome: FAILED** under unchanged 99% whole-run and steady delivery criteria, five-seat 200 hunters/40 teams, original real Qt server and load generator. The load harness is synthetic loopback clients running on a hosted Linux GitHub runner, not real 5-PC play, Windows network, Direct P2P or live Fornex. Preserve this result even when tests of source compilation pass.

| 200-client case | Players Playing | Teams | Steady entries received / sent | Steady % | Qt Game Data ingress | Qt Game Data egress | Kind-3 5s sampled windows |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 shard / 1 enemy owner | 200 | 40 | 380,448 / 405,488 | 93.82 | 264,596 | 264,596 | 6 |
| 3 shards / 1 owner | 200 | 40 | 115,999 / 122,820 | 94.45 | 205,588 | 205,588 | 16 |
| 1 shard / 5 owners | 200 | 40 | 1,265,999 / 1,487,820 | 85.09 | 624,476 | 624,476 | 6 |
| 3 shards / 5 owners | 190 | 38 | 484,429 / 556,092 | 87.11 | 541,436 | 541,436 | 17 |
| 3 shards / cross-code / 1 owner | 200 | 40 | 296,245 / 305,444 | 96.99 | 229,516 | 229,516 | 15 |
| 3 shards / cross-invite / 1 owner | 200 | 40 | 25,453 / 27,848 | 91.40 | 181,040 | 181,040 | 16 |
| 3 shards / cross-mixed / 1 owner | 200 | 40 | 212,946 / 230,536 | 92.37 | 224,008 | 224,008 | 17 |

**Actual run facts:**
- Each of the seven test scenarios reported `udp_write_failed=0` and `udp_write_short=0` for original Qt bbload game sockets and `udp_buffer_drops=0` for the host-level Linux UDP receive-buffer counter. These **do not prove delivery to a particular client**.
- The original Qt LinkServer `YT130_WIRE_TRAFFIC kind=3` aggregate counted precisely equal ingress and egress Data datagrams over its full **reported 5-second windows**, on *every original shard*. This is an actual source-backed observation that the relay successfully **submitted** outgoing datagrams at that level. It does **not** establish that the receiving socket consumed them, nor that Qt's logger includes the final partial window, nor how many **game entries** were inside each Data datagram.
- Real Qt server median/p99 relay latency was low for **received and accepted frames** (p99 ~2.65–7.48ms). Low latency for received frames does not imply low packet loss or no frame backlog.
- The original load generator increments `packets_sent` per **embedded game entry** inside an outgoing `ServerLink::Data` datagram; `packets_received` increments after game-frame decode. The `kind=3` Qt wire counter increments **once per datagram**. It is invalid to subtract one from the other as if each Data datagram always contained one entry. The one-owner cases counted `packets_lost=0` sequence gaps while having substantial entry-count discrepancies; the five-owner cases recorded ~110k–127k sequence gaps. This makes generator state, truncation/period boundaries, receiver scheduling and peer readiness important candidates for separate investigation, not proven causes.
- `cross-invite` formed all 40 teams in this run, unlike previous V141 three-shard invite-only run that left **15 in Lobby**. Invite failure is therefore intermittent in the tested environment. It still had 91.40% steady game entry delivery and only a 1.5-second minimum steady window. Unrelated names, tokens, IPs and raw logs were intentionally not retained.

**Next discriminators, no threshold lowering:**
1. **Actual refused TeamLobby actions:** V156 instruments only anonymous categories for `LobbyState.notice` on the *existing* real bbload; `name_absent`, `name_ambiguous`, `lookup_throttled`, other, total, to establish whether a cross-shard directory-presence race is happening. These values are *reply-event counts*, not distinct users. Original TeamLobby::Request has max five failed name/code lookups per 60 seconds. Do not disable anti-enumeration/anti-bruteforce for an unconfirmed race.
2. **Generator receiver saturation / edge-window artifact:** record bounded per-worker process CPU and receive-queue processing delay, per-stream first and last frame, and actual Data datagrams received and parsed. Quantify whether pre/post steady read drain or cross-worker startup skews the entry ratio. Keep generator and actual server CPU distinct.
3. **Client kernel receive buffer:** compare per-UDP socket drops and polling fairness, not only aggregate `Udp RcvbufErrors`. Measure how QoS changes under fewer simultaneous simulated sockets per worker (4 vs 8 vs 16 bbload processes) at the **same total 200 players**. If packet delivery improves with more worker processes, loadgen scheduling is likely involved; if not, continue server/transport tracing.
4. **Only if server is the bottleneck:** evaluate bounded batching/send-queue prioritization and server tick coalescing using original C++ source and regression tests. Cross-shard invitation directory synchronization is a separate subsystem.
5. **P2P release gate:** true five-hunter physical Windows LAN/WAN encrypted Direct P2P, NAT fallback, idle timer, rekey/consent and 200 concurrent users remain untested and OFF in any public client.

**Interpretation:** V155 diagnosed a real loss of **delivered game entries** under load, but did **not** prove 15% packets were dropped inside the Qt relay itself. Any claim that reducing the server's packet threshold or switching to Direct P2P magically fixes this would be unfounded.

This evidence is intentionally aggregate-only and belongs to the DRAFT server diagnostic PR. Do not deploy to Fornex or claim a production capacity pass.
