# Actual optimized Yharnam Together 1.3.0 synthetic loopback capacity curve

Captured from [GitHub Actions run 40382037557](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40382037557), its [artifact 12681526484](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40382037557/artifacts/12681526484) and original official v1.3.0 `server/loadtest/bbload.cpp`.

**Not a player count supported in production.** The game-to-server traffic was relayed on one Ubuntu CI host, all simulator processes on the same machine, synthetic teams of two, fresh synthetic accounts, the temporary build check disabled ONLY for `bbload`, standard 30 owner/8 follower frames per second, 100 ms between each client start and optimized -O2 native Qt server code. There is no physical two-PC test, direct gameplay P2P, production Fornex, or proof of hardware independence.

| Synthetic peers | PLAYING | client aggregate received/sent | relay p99 (ms) | main thread avg CPU (% of one core) | client-observed server out (Mbit/s) | max shadNet RSS (MiB) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 4 | 100.00% | 0.430 | 0.9 | 0.164 | 27.9 |
| 16 | 16 | 100.00% | 0.391 | 1.8 | 1.173 | 28.0 |
| 32 | 32 | 100.00% | 0.662 | 3.6 | 5.385 | 28.6 |
| 64 | 64 | 97.96% | 262.676 | 18.6 | 47.605 | 43.4 |
| 100 | 100 | 60.53% | 2859.115 | 84.1 | 307.791 | 232.7 |
| 200 | 46 | 20.08% | 4100.207 | 99.2 | 313.772 | 235.9 |

**Important methodological qualifiers:**
- `PLAYING` is a state flag, NOT proof of a smooth game. The previous quality predicate erroneously labeled 64 and 100 as `FULL_GAMEPLAY` despite loss and multi-second tail latency.
- Ratios are aggregate application packet counts, NOT a per-client delivery guarantee; use as a synthetic degradation signal. At 100, `packets_sent=54435`, `packets_received=32951`. The 200-peers state was `46 PLAYING`, not 200 active players.
- `udp_buffer_drops` comes from host-global `/proc/net/snmp` and mixes sockets of shadNet and generators: 45,798 at 64, 930,662 at 100, 1,661,876 at 200. Do NOT call these exclusively server-side packet drops.
- `server_out_mbit` is computed from all client `bytes_received`; not exclusively reliable gameplay UDP and not direct NIC accounting. Relay delivery and latency must be checked separately. At high loads, unexpected amplification/service traffic must be profiled before attributing a root cause.
- `accounts_worked=0` in all stages because non-hosted benchmark does not use hosted signup work. `refused=0` in all stages. A 100k-round synchronous SHA256 signin in the main thread is still a source-level risk for connection floods, but these measurements implicate severe throughput/backpressure even after successful link/login; they do not prove that password hashing alone caused packet loss.

**Code-grounded observations:** official YT v1.3.0 `server/src/link_server.cpp` `OnReadyRead` drains all pending UDP datagrams in one Qt event-loop callback; `HandleLink` calls `m_link.Receive` and `Apply`, including datagram writes. It is a single-threaded hot path. This is a possible fairness/bottleneck contributor, not an isolated proof of one faulty function. Server world and protocol fan-out, cryptography, Qt generator load, and kernel queues still need a controlled comparison.

**Next experimental intervention (not a live fix):** use the same exact 1.3.0 pinned server, account/test conditions and the original generator with reduced `--owner-fps 10 --follower-fps 3` at 32,64,100,200 peers. Compare per-stage delivery, relay p99, CPU, bytes received and completed game states with the full-rate curve. Keep results in a separate `yt130-reduced-rate.jsonl` artifact even if one stage is unhealthy. Reduced traffic is diagnostic ONLY; never silently ship reduced game update frequency as an optimization. A server-side event-loop/profiled hot-path experiment should follow ONLY when this delta is measured.

**Fail-closed gate added:** in localhost CI, `quality()` now requires all peers PLAYING with meaningful aggregate packet delivery, at least 99% aggregate delivery, relay p99 <= 50 ms, and main-thread CPU below 75%. These are conservative test acceptance budgets, not verified product/SLA guarantees and not per-client measurement. The first degraded stage halts the standard benchmark; the separate reduced-rate profile is a diagnostic report, never a successful 200-player claim.

**Safety:** all code stays in an isolated branch/PR, uses disposable loopback servers and test DB only. Real Fornex, CLS Friends, `master`, actual account DB and saves are not touched. Direct gameplay P2P remains OFF until authenticated peer consent, session keys, replay protection, NAT traversal, relay fallback and real two-PC tests.
