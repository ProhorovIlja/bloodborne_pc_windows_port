# V235: unbiased, bounded BBHost/BBPort/Lantern comparison gate

2026-11-01. Draft PR #85 (playable track). No claim of actual measured
BBHost-vs-BBPort superiority or functional interoperability.

## Why

Owner requirement is to choose **the best playable Bloodborne runtime**,
not to stay with BBPort for branding reasons. BBHost is a legitimate possible
foundation, particularly for native x86-64 execution and network throughput.
This choice must not sacrifice Yharnam Together's seamless co-op, player HUD,
boss sessions, five-player support, world transitions or save safety.

BBHost public host clocks use QPC, and its published online description
includes direct UDP/STUN. YT v1.3.1 has different server and runtime contracts.
These are implementation features, not independently comparable FPS/network
benchmarks and NOT proof of binary/protocol compatibility.

## Added in this change

- `compare_runtime_evidence_v235.py`: offline, read-only JSON gate. Accepts
  one limited 128 KiB measurement *summary* per runtime, not game logs.
- Enforces identical game, patches and mods hashes; machine, OS, driver,
  resolution, render settings, scripted scene, team size, NAT topology, server,
  warm-up and timed capture conditions. Explicit pinned build commit.
- Requires 3–20 individually identified runs for each runtime, separately
  verifies finite, nonnegative numerical fields and zero safety failures.
- Compares medians of 1% low FPS, p99 frame time, server CPU, server outgoing
  Mbps, p99 join time, loss, and direct P2P rate; rejects any >5% regression,
  a >5 percentage-point direct-P2P loss, or candidate crash/actor/save/join
  errors. A meaningful >=5% performance gain is required for a provisional pass.
- Includes synthetic tests on Windows/Linux. Passing does NOT authorize
  runtime migration, server rollout or a compatibility claim.

## How to get *actual* input evidence

Capture three or more separate runs on the SAME pinned Windows hardware,
OS/driver, Bloodborne 1.09 files and installed patches/mods, scene, scripts,
team count and network topology. Use exactly the same capture duration,
warm-up, and test server. Record metadata and concise medians with the
schema in `compare_runtime_evidence_v235.py`; never transmit retail files,
tokens, private captures or entire logs. Repeat 2-player and 5-player
scenarios separately, plus open/restricted/symmetric NAT, fallback cases,
late joins and map transitions. A real five-client run also needs an
independent visual/actor/saves regression checklist.

Run `python playable-track/compare_runtime_evidence_v235.py --baseline
PRIVATE-yt.json --candidate PRIVATE-bbhost.json --output PRIVATE-result.json`.
Exit 0 means only that the declared numeric conditions passed in an
*unverified offline report*. Exit 2 rejects invalid evidence; 3 means valid
but candidate performance/safety gate failed.

## Source links and constraints

- https://github.com/droogie/bbhost (source reviewed at
  3b0c62939395ebfd8af8b8e365d49418c53084e3 for timing)
- https://github.com/lKaniel/bloodborne-server/releases (v1.3.1)
- V233 existing YT shadNet loadtest acceptance gate still independently
  determines server performance within YT. V235 is a cross-runtime contract.
- Current five-slot upstream changes #484/#486 are Draft, not a released
  compatibility proof.
- No change to production Fornex; no game binary or private measurements
  are committed; GitHub CI result needs inspection after push.
