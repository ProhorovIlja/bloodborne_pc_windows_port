# V237: closing server capacity regression blind spots

Date: 2026-11-01. Playable track Draft PR #85.
This changes the existing V233 offline shadNet loadtest gate, not production YT.

## Verified code issue

V233 compared playing count, refused joins, UDP receive-buffer drops,
main relay-thread CPU, relay latency, egress and RSS, but merely *reported*
total server CPU and welcome p99. It did not compare lost packets at all.
A release could therefore be rated PASS despite much higher total CPU,
excessive join latency or growing packet loss. These matter for the small
Fornex VPS, especially in any eventual direct P2P / relay fallback mix.

## Implemented in existing tool

`playable-track/yt_server_capacity_gate_v233.py` now additionally rejects:
- total server CPU more than 5 percentage points above baseline;
- p99 welcome/join latency more than 25 milliseconds above baseline;
- increase in packet-loss ratio (lost / sent) by more than 0.0005 absolute.
  Ratios rather than raw counts are necessary because moving gameplay UDP
  off a relay changes the number of server-observed packets.
- zero packets sent in a supposedly active-player loadtest, or reported lost
  packets greater than sent packets, to avoid invalid loss denominators.

The regression allowances can be configured with
`--max-total-cpu-regression-points`,
`--max-welcome-p99-regression-ms` and
`--max-packet-loss-rate-regression`. Negative or nonfinite allowances
are rejected. Existing V233 gates remain in force.

`test_yt_server_capacity_gate_v233.py` covers cases where relay-thread
CPU and bandwidth improve but the new metrics regress, as well as
packet-volume normalization and impossible input reports.

## Scope and evidence

These are *synthetic test fixtures* against the published shadNet
`run_load.py` summary schema. No live measurements or 200 real YT players
were run here. The tool must not claim actual P2P/NAT efficiency,
five-client gameplay parity, or production Fornex readiness.

The existing `.github/workflows/yt-v233-server-capacity-gate.yml` is
expected to run both Windows and Ubuntu tests on changes to these files.
Check actual CI results before labeling V237 green.

No changes were made to the live server, save files or retail game binaries.
