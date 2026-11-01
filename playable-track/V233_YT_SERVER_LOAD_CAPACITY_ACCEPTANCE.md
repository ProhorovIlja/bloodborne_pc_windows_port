# V233: source-verified YT server capacity gate, not a fake P2P benchmark

2026-11-01. Draft YT playable PR #85, official YT v1.3.1 source:
`lKaniel/bloodborne-server@5d2305ee611ef1e03be39ff925f0da75c9a70393`.

**Motivation:** user's Fornex VPS must not relay the entire continuous
gameplay stream for hundreds of players. Only legitimately necessary,
server-authoritative matchmaking, membership, room/world state, saves
and fallback traffic should consume the shared server. Eligible direct
P2P needs authenticated, per-channel switching, not an unconditional
server relay.

## Actual existing benchmark format

Original `server/loadtest/run_load.py` already launches its own
temporary shadNet process plus synthetic `bbload` clients. It prints
one compact JSON summary including:
- effective players, playing sessions, refusals, packet loss;
- `server_cpu_avg`, `main_thread_cpu_avg`, memory;
- `server_out_mbit`, `server_in_mbit`;
- `relay_ms_p99`, `welcome_ms_p99`,
  `udp_buffer_drops`.

V233 did **NOT** invent new load metrics or claim a real YT P2P
performance boost. It adds
`playable-track/yt_server_capacity_gate_v233.py`: a read-only
comparison gate against two genuine original-format summary files
(`--baseline`, `--candidate`).

It accepts exactly one bounded JSON summary per input, rejects
missing/nonfinite/negative metrics and incomparable player counts,
and marks FAIL if a candidate loses playing sessions, adds refused
connections or UDP buffer drops, or exceeds explicit budgets for
the main relay thread's CPU, p99 relay delay, server outbound
bandwidth, or maximum resident memory.

The default simulated nonregression tolerances are:
- main thread average CPU: at most **+5 percentage points**;
- p99 relay latency: at most **+10 ms**;
- server outbound bandwidth: **no increase**;
- max server resident memory: at most **+50 MiB**.

These are **provisional safety gates**, not universal performance
targets; compare only same hardware, build settings, number of
players, team size, traffic mix, duration, warmup and network profile,
and rerun enough trials for meaningful conclusions.

Example (PRIVATE test outputs only, without production deployment):

```bash
python playable-track/yt_server_capacity_gate_v233.py \
  --baseline /PRIVATE/baseline-runload.json \
  --candidate /PRIVATE/candidate-runload.json \
  --max-main-cpu-regression-points 5 \
  --max-relay-p99-regression-ms 10
```

The companion synthetic test validates lower traffic, lower main
CPU, loss/refusal regressions, incomparable player populations,
invalid JSON and nonfinite values. Public matrix CI validates the
existing original YT v1.3.1 `run_load.py` JSON field names on
Windows/Ubuntu and runs only fictional numbers, not Fornex metrics.

**This does NOT demonstrate live P2P, NAT traversal, 5-seat gameplay,
actual CPU savings, or user server capacity.** It is a measurable
release gate for future source changes and honest comparisons. Do not
deploy until passing actual staging load and gameplay tests.

## External source priorities for real implementation

- `visy/bloodborne_pc_windows_port` at
  `79889e01f173ac656fb969255ee2d921b13f0e99`:
  `docs/party/network_robustness.md` documents reliable host
  control + peer UDP with NAT hole punching/relay fallback, and
  deterministic simulation for jitter/loss/outage. Study the
  reliability/sequence and simulation *design* to construct
  independent YT integration.
- `droogie/bbhost`: public P2P UDP/STUN, server-backed online
  matchmaking and alternative GPU performance instrumentation.
  None proves YT crossplay and neither can be transplanted without
  protocol/schema and GPL review.
- Official YT `server/loadtest/run_shards.py` provides additional
  multi-shard server exercises. The next stage should quantify
  authoritative workload separately from direct candidate movement
  paths, not combine the two into one misleading throughput number.
- Upstream YT PR #484 and #486 five-seat changes remain DRAFT at
  observation; no production server/team-size change.

## Related launcher/source integration

V232 mod preflight uses actual YT `bbport/scripts/mods.py` from
v1.3.1, and its optional final-winning-gameplay-file fingerprint
can become one field in a future authenticated party compatibility
proof. Full handshake also needs correct client build, game baseline,
params, executable patches, session protocol and party rules.
See `V232_YT_LAUNCHER_MOD_COMPAT_AND_UPSTREAM_PLAN.md`.
