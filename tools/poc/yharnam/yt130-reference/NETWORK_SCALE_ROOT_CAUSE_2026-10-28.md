# Yharnam Together 1.3 native server: evidence-based 1,000+ active player plan

Status: **2026-10-28, exploratory and source-pinned, no production changes.** The real game client and actual two-PC WAN play have not been tested at this load. Hosted synthetic "PLAYING" is stronger than registered connections but still not human gameplay. Absolute improvements in parallel GitHub-hosted runs must not be attributed solely to one patch: CPU/worker contention differs across runners.

## 1. Source and measured root cause: Qt main loop starvation

Source: original [lKaniel/bloodborne-server](https://github.com/lKaniel/bloodborne-server/tree/0645740a33ae21c56df3b4a0d9777086dbca6053) commit `0645740a33ae21c56df3b4a0d9777086dbca6053`:
- `server/src/link_server.cpp::OnReadyRead` drains every datagram in **one unbounded while loop** and calls `HandleLink` synchronously, which can run world/server Apply.
- `OnWorldTick` uses **the same Qt event loop** and fires from a 50ms `QTimer`.
- `server/src/bloodborne_world.cpp::Service::Tick` also loops over all member streams, games and world functions; missed timer deadlines delay reliable ACKs and world state publications.

**Actual [PR41 original C++ CI artifact](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40684093675/artifacts/12815336410)**, `yt130-wire-logs/wire-stages.jsonl`, reports:

| Synthetic peers | Longest single UDP read/HandleLink callback | Longest world-timer dispatch gap | Reliable Coop(7) outbound | Data(3) outbound |
|---:|---:|---:|---:|---:|
| 32 | 213ms | 222ms | 2.9 MB | 1.5 MB |
| 64 | 555ms | 561ms | 15.3 MB | 3.9 MB |
| 100 | 774ms | 809ms | 41.8 MB | 10.5 MB |
| 200 | **967ms** | **1,016ms** | **200.0 MB** | **23.5 MB** |

The 200 stage additionally logged 22,086 retransmitted reliable entries, 2,833 ACK-only frames, `max_read_batch_datagrams=5800`, 62 late world-timer ticks, and RELAY_LATENCY/DELIVERY_DEGRADED while 200 simulated users were nominally PLAYING. Kind(7) accounts for ~89% of these two dominant outbound traffic classes; moving just Kind(3) to P2P does not solve this CoopStream load.

**Experimental [PR44](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/44)**: cap each `OnReadyRead` callback at 128 datagrams or ~2ms checked every 16, queue exactly one lifetime-guarded Qt continuation if datagrams remain. Continue until the kernel queue empties; never intentionally discard a packet or weaken auth. Parent source-pinned Hosted roster + world indexes remain intact. Measure whether `max_read_batch_us`, `max_world_gap_us`, late ticks, Coop resends and relay p99 improve. If kernel drops rise, reconsider budget and socket pressure; yield is not a substitute for total receiving capacity.

Qt docs: [QUdpSocket readyRead semantics](https://doc.qt.io/qt-6/qudpsocket.html). Leaving pending datagrams **without** explicitly resuming reads is a correctness bug.

## 2. Real Hosted 1 / 3 shard active test, not just registration

[PR40 original baseline](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40684086554) vs [PR41 indexed roster](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40684093675):

| Players / topology | Original baseline PR40 | Indexed roster PR41 |
|---|---|---|
| 250 / 1 | FULL_GAMEPLAY 250 | FULL_GAMEPLAY 250 |
| 250 / 3 | CROSS_SHARD_JOIN_TOO_SLOW 250 | FULL_GAMEPLAY 250 |
| 500 / 1 | RELAY_P99_OVER_50MS 500 | FULL_GAMEPLAY 500 |
| 500 / 3 | CROSS_SHARD_JOIN_TOO_SLOW 500 | FULL_GAMEPLAY 500 |
| 1000 / 1 | PARTIAL_PLAYING 950 | 1000 playing but GAME_PACKET_LOSS |
| 1000 / 3 | PARTIAL_PLAYING 644 | PARTIAL_PLAYING 920 |

PR41 1000 / 1: 39,256 synthetic packets lost, 1,303,731 received, 46,231 host-wide Linux UDP receive-buffer drops, relay p99=101.3ms; per-shard main thread 59.8% of one core, whole process ~186.5% core, 4-core test host load avg 2.75. PR41 1000 / 3: 920 PLAYING, 0 observed kernel drops, relay p99=98.3ms, redirect p99=2,057ms, **4-core** test host load avg 8.91, three server processes each ~104–106% single-core use *in addition to synthetic players and Redis/directory*. This is CPU oversubscription and redirect/backpressure evidence, not proof a 4-core production VPS will fail identically.

**Critical methodological gate**: measure 1-/3-/6-shard under matching controlled compute allotment, separate load clients from the server host (otherwise the generator competes for cores), same exact traffic/seed/ramp and packet count. Record steady-state RSS, per-shard main and process CPU, Linux drop counters, redirect p50/p99, Coop resend/ACK, actual PLAYING, active sender+receiver packet deliveries, and clock-stall intervals. Synthetic packet generators are not a replacement for actual two-machine NAT/WAN tests.

## 3. Source-backed priority queue

1. **P0: Event-loop fairness and Linux receive losses.** Native PR44 first, measure improvement and rollback if worse. Do not raise buffers blindly. Observe `/proc/net/snmp` `Udp: RcvbufErrors`, per-socket drops and actual syscall volume. Combine socket changes with auth/rate-limit protections.
2. **P0: Cut Coop(7) *semantically*, not simply drop it.** Service sends frequent `VitalsBoard`, `LobbyState`, `MapBoard`, `Entries` through an ordered reliable stream; at 200 peers the synthetic server logged 24,471 `VitalsBoard` and 11,886 `LobbyState` envelope publications. Trace repeated identical data, interest membership and truly necessary reliability. Explore opt-in delta/diff snapshots for client/version matched pairs, per-world/party scope, and publication coalescing. Never weaken server-authoritative rewards, host authority, trades, invasions, ACK or persistence.
3. **P1: Avoid quadratic repeated resend scanning.** Original `coop/game_link.h::GameLinkPeer::Flush` scans `entries` for each due unacked resend. Source-pinned [PR43](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/43) uses reliable sequence membership instead and native C++ 320-message ACK/backoff/64-resend regression; verify before merging. A true resend storm should trigger per-peer congestion accounting and bounded reliable in-flight windows, not unlimited bursting.
4. **P1: Keep world lookup per player and stable.** Source-pinned [PR41](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/41) avoids repeated Hosted all-roster and all-invites scans. [PR42](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/42) avoids all-world scans on recipient-specific Hosted lobby state; rebuild cached indices on restore/re-sort. Preserve nonHosted compatibility and private world lists.
5. **P2: Linux UDP batching once P0 metrics support it.** `recvmmsg`/`sendmmsg` amortize syscalls but using them from a Qt QUdpSocket requires carefully owned socket descriptors and no dueling readers. Start Linux-only experimental implementation behind a feature flag with precise packet ordering, error handling, MTU, auth and fallback. Sources: [recvmmsg(2)](https://man7.org/linux/man-pages/man2/recvmmsg.2.html), [sendmmsg(2)](https://man7.org/linux/man-pages/man2/sendmmsg.2.html).
6. **P2: More cores and actual sharding without false flow affinity.** Linux [RSS/RPS](https://docs.kernel.org/networking/scaling.html) and `SO_REUSEPORT` can distribute kernel receive work, but blindly sharing shadNet's game/session socket between independent workers may separate a game from its authenticated state. Test stable endpoint affinity / BPF routing or separate shard ports + directory. `SO_REUSEPORT` by itself is not a cross-shard session broker.
7. **P2: Authenticated Direct P2P with relay fallback.** Preserve server admission/team/auth/world/Coop7/RPC8 as needed. Only the explicitly eligible Data3 subset routes between client peers with authenticated candidates, NAT punching/ICE and timeboxed fallback. Valve's [GameNetworkingSockets](https://github.com/ValveSoftware/GameNetworkingSockets) demonstrates ICE/P2P, encrypted packets, ACK-vector and lanes; [ENet design](https://github.com/lsalzman/enet/blob/master/docs/design.dox) demonstrates reliable windows, pacing, backoff and bandwidth control. These are **reference architectures**, not wire-compatible modules to copy wholesale. Both peers require matching client logic.

## 4. Acceptance criteria (none proven at 1000 yet)

- 1000 active senders/receivers with authentic 30fps owner / 8fps follower loopback load, **1000 PLAYING**, no requested packets omitted, >=99% end-to-end expected game delivery, no Linux UDP drops, relay p99 <=50ms, redirection p99 <=2s, stable per-shard single-thread CPU <75%, bounded queued Coop bytes and no runaway resends.
- Repeat for 1 vs 3 shards with **independent load hosts**, repeat 3 runs on identical dedicated hardware and report distributions and confidence, then load-spike to 2000 separately only after 1000 meets all gates.
- Original 11 native Qt CTests, auth/security restrictions, 4-player join, PvE/PvP restore, no client regression. Two actual PCs with CGNAT and UDP-blocked cases must demonstrate secure relay fallback before calling Direct P2P finished.
- Never deploy any experimental result to Fornex/CLS Friends, rename a live build identity, share account keys, overwrite game saves or merge into master automatically.
