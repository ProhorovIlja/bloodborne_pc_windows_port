# Nightwatch Co-op source evaluation (2026-10-22)

Repository: https://github.com/vladtepes22/NightwatchCoop
Release inspected: `v0.2.0-beta.10.1` (published 2026-10-22).
License: GPL-3.0 for combined code; retain upstream notices and attribution.

## Confirmed lineage and scope

Nightwatch combines **Lantern Engine 0.9.36 (Awaken)** with **visy's party co-op 0.7.1** on native Windows. It credits Artificial-Sweetener/BloodBorneButPc for the first such integration; it is not a distinct multiplayer protocol.

The Nightwatch README explicitly says there is no public online play, no connection to The Hunter's Dream, and no central server. It uses direct PC-to-PC connections with BBP3 party codes, and optional NAT / VPN / member-relay mechanisms from visy's co-op lineage. It is **not** a ready Seamless Hunt adapter or a solution to current BBSC shadPS4 compatibility.

Nightwatch's older `INTEGRATION.md` describes initial 0.6.5 / Lantern 0.9.29 work, whereas its newer README and release notes describe 0.7.1 / Lantern 0.9.36. Use the newer release scope; do not treat the integration note's local test counts as validation of the newest build.

## Verified source comparisons

- `Nightwatch/engine/gpu/shim/party/party_netpath.cpp` is byte-for-byte identical to `visy/gpu/shim/party/party_netpath.cpp` in the current user's fork (both Git blob e7b50b009550b28b4ecaa568831562170997412a).
- `party_rdv.cpp` is also byte-for-byte identical (blob 17dd1505ef3924f7ad6624b0f43a0c2104b2b791).
- `party_crypto.cpp` is also byte-for-byte identical (blob deeef2500682db5cc6721f0de623b671e3ea7467).
- `party_death_rules.h` differs (visy fork 65,977 bytes, Nightwatch 56,999 bytes), consistent with visy's newer party rules. Examine commits for any specific Nightwatch fix before importing; never overwrite newer visy with older co-op sources.

## Highest-value candidates for a single Seamless Hunt native client

1. **Engine integration strategy.** Study Nightwatch's adaptation of visy's co-op hooks to Lantern's runtime, particularly single ownership of per-frame hooks and of game menu/talk hooks. Reference: `INTEGRATION.md`, `engine/gpu/shim/party`, engine entrypoints and `tools/build-engine.ps1`.
2. **Awaken performance techniques and toggles** referenced in `engine/CHANGES_AWAKEN.md`: VRAM pressure reclamation, frame pacing, async pipeline compiling, draw-thread lookahead, occlusion culling, loading path. Many may overlap existing visy code, be incompatible, or regress stability. Benchmark on same hardware and scene before integrating.
3. **Single Windows WPF launcher UX.** The `launcher/windows/BloodborneLauncher` code has native graphics/engine controls, co-op and member management, save tools, and user-facing updates. This can inform a future Seamless Hunt launcher, but replacing visy's current Python/Tkinter launcher needs packaging and regression tests.
4. **Update design.** `launcher/windows/BloodborneLauncher/Core/Updater.cs` preserves saves/settings/mods and stages downloaded files; beta 10.1 fixes DLL file locks. But manual inspection did not find an SHA-256 or digital-signature verification of downloaded archives and the copy is not fully transactional (file-by-file over install). Use ideas only, add authenticated manifests, integrity verification, and a true rollback mechanism before distributing as Seamless Hunt.
5. **Game testing workflows.** `tools/smoke-game.py`, `tools/smoke-coop.py`, `engine/docs/SEAMLESS_TESTING.md` are useful references for isolated headless host/guest tests, save checks and performance p99 thresholds. These do **not** establish two-machine Internet reliability or visible rendered FPS.

## Decision

**Keep exactly one user-owned GitHub fork**: `ProhorovIlja/bloodborne_pc_windows_port`, branch `feature/seamless-hunt`. Preserve its newer visy 0.7.2 party, NAT, saves and direct P2P stack. Nightwatch becomes another source-of-truth reference, **not a second deployed client, not a second server, and not a fork the user has to maintain**.

Continue building the optional Seamless Hunt discovery/auth integration against the server source contract. The existing read-only server diagnostic already lives in this branch. Do not claim cross-protocol BBSC interoperability until actually implemented and tested.

Test Awaken/Lantern integration as a controlled, isolated engine experiment on the same branch (separate commits) after establishing Windows build and two-PC baseline; do not take the entire Nightwatch directory or replace the runtime on faith. Any selectively reused GPL code requires appropriate notices and attribution.
