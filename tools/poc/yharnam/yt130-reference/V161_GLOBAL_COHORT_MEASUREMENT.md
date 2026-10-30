# V161: shared-send-time cohort to distinguish measurement skew from real UDP/game loss

**Status: DRAFT, diagnostic-only; exact native original Yharnam Together 1.3 Qt source.**

## What previous original evidence proves (and does not)

The old 200-hunter, 40-five-seat-team tests V155/V157/V158/V159 had 82-97% game-entry ratios while original Qt LinkServer showed matching *sampled* incoming/successfully submitted outgoing game Data datagrams. Original bbload confirmed no UDP read errors and every *received* game Data datagram decoded. This does not prove no frames were lost before the receiver, nor that all game entry ratio deficits reflect genuine kernel/server packet losses. Existing per-sender sequence gaps must still be investigated.

Source review of original Qt `bbload.cpp` and our V120 staging reveals a potentially serious **test measurement mismatch**:

- Each child Qt `Load` independently arms `steady_since_us` when its own players are all Playing and teams complete. For 200 players / 4 processes, this is 50 local hunters at a time, **not a single instant when all 200 are ready**.
- The sender increments `steady_packets_sent` as soon as its local gate opens; its target receiver may run in another Qt process whose gate is not open yet. The receiver counts the incoming entry in `steady_packets_received` only if the *embedded sender timestamp* is after its own independently armed gate. This can omit legitimate game entries that were sent during the unaligned interval. For V120, sums across processes are **not a population-wide synchronized window**.
- This may contribute to missing entries in the reported percentages. It does not explain all five-owner `packets_lost` sequence gaps, and is not a claim that our server is already fast enough.

## Actual V161 implementation

`stage_global_cohort_v161.py` is source-pinned to original `0645740a33ae21c56df3b4a0d9777086dbca6053` and original Qt `bbload.cpp` Git blob `edfb6ea39b898cca2638d65826981cf9fc81c334`. Applied after V120/V158/V159 only in an isolated CI checkout. Game protocol, server routing, gameplay and production are unchanged.

Each genuine `Game::SendGamePackets` increments a count of **embedded game entries** in a one-second `std::chrono::steady_clock` bucket keyed by `now_us`. `Game::TakeData` increments the receiving count in the **same** bucket keyed by the existing embedded sender `sent` timestamp. Because all Qt subprocesses run on the same Linux host, `steady_clock` has a common time base here.

Each child emits only anonymous aggregate per-second counts and when its local 5-hunter teams were all Playing. The original Python shard parent computes:

1. Last readiness instant across ALL worker processes.
2. Earliest worker finish minus two seconds for UDP receive/drain tail.
3. Whole one-second buckets inside that common interval, at least five complete seconds.
4. Total sent and received game entries for exactly those same sender-time buckets across all 200 hunters.

The new `cohort_quality`, `cohort_seconds`, `cohort_packets_sent`, `cohort_packets_received` are **a separate diagnostic**. Previous `quality`, original V120 `steady_quality`, 200 Playing, 40 teams, 99% threshold, sequence-gap and CPU limits remain unchanged and cannot become green due to a good new cohort score. Missing, malformed or duplicate source bucket evidence fails closed.

## Regression coverage

`test_stage_global_cohort_v161.py` executes the real generated Python aggregator with two simulated worker responses: 12s vs 17.3s readiness aligns at 18s, and 99.5% actual aligned delivery is correctly represented; real 25% loss stays red; incomplete teams, too-short intersection, invalid buckets and duplicate seconds are rejected.

`test_grade_global_cohort_v161.py` asserts no false positive if previous strict QoS is red, even when common cohort is 99%+; incomplete cohort fields and inconsistent/count-forged metrics are rejected.

## Verification

- Source/stage CI: [#41101574486](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41101574486) **QUEUED at the recorded checkpoint**; no source or compiler success yet.
- Real original Qt/Redis/shadNet 200-hunter 4/8/16-worker A/B: [#41101591056](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41101591056) **QUEUED at checkpoint**, not measured. It recompiles the real Qt original C++ and preserves the original two independent ratios in its private artifact.
- Previous actual original V158/V159 five-hunter run [#41097996435](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41097996435) completed successfully as diagnostic but strict 99% gameplay delivery **FAILED** in every scenario. See `V158_V159_OBSERVED_200PLAYER.md`.

## What would change the recommendation?

If the global aligned cohort ratio is near 99% while V120 legacy reads 85%, focus on **measurement and readiness synchronization**, and separately investigate confirmed sequence gaps before claiming production capacity. If both ratios remain 85%, focus on kernel UDP drop attribution, server/client receive pacing, per-socket buffering and original game-data relay scheduling. If fewer than 5 seconds of true all-player common readiness, classify **insufficient evidence**, never pass. In every case real Windows five-PC LAN/WAN Direct P2P NAT, consent, authentication/rekey, save safety and long-running gameplay still require hardware testing.

No real game data, credentials, private endpoints, names or saves are captured in this experiment. No Fornex, `master`, public client, or release is touched.
