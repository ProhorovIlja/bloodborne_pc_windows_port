# Seamless Hunt: single integrated server + client + launcher (priority 2026-11-06)

## Product decision

**All active development prioritizes a single excellent, tested Seamless Hunt multiplayer product.**
This means **server + game client + BLauncher + safe updater** as one release contract.
Other independent research is deferred, not a prerequisite and not a release blocker for this product.

The goal is the best *measured, compatible* features from released Yharnam Together v1.4.0, CLS BBSC,
BBHost, BBPort, shadPS4, verified forks/branches/PRs, game/launcher QoL projects, and
appropriate open-source networking components. Never merge code merely because it is newer.
Track original source commit, license, Windows/Linux build status, game-version compatibility,
benchmark evidence, rollback, and real multiplayer reproduction for each adopted feature.

## Shipping architecture

| Area | Intended outcome | Current evidence / blocker |
| --- | --- | --- |
| One server | Existing YT shadNet + world/party/auth service, Hosted=false; robust sessions, five total team slots, friends/filters/invites, host handoff, invasions/duels, persistence, rate limits and monitoring | Existing production server is separate from GitHub experiment; no automatic production replacement; end-to-end 5-player proof pending |
| One account database | Existing seamlesshunt.com registration identity used by both supported clients without duplicate accounts | Registration implementation and its working DB are on Fornex; protect CSRF and existing accounts; full mixed-client sign-in proof pending |
| Game client | BBHost candidate for runtime/performance; retain verified BBPort fallback until replacement beats it in real tests | PR #86 has authenticated source-only YT protocol integration through V420 including encrypted SnapshotRequest and read-only Snapshot metadata. **NOT** working in-game BBHost NetSync. PR #85 holds alternative BBPort/hybrid research |
| Real online transport | End-to-end authenticated YT server link and party/world authority; direct P2P where authenticated and safe, server relay fallback with bounded server bandwidth | Original transport and cryptographic/protobuf synthetic tests exist; game NetSync, granted direct peers, NAT matrix and real 5-player soak pending |
| Launcher | One BLauncher with client choice, one coherent installation/update flow, safe independent engine settings, mod manager, install integrity, rollback and diagnostics | BBHost launcher V6 is experimental; packaged CLS v1.0.0 currently ships BBPort and BBHost editions separately, not a proven unified auto-updater |
| Gameplay and QoL | Start from released original YT v1.4.0: five-hunter UI/party, duels, global quick match, host handoff, boss/NPC/world fixes, phantom-glow option, spectating, localized launcher and team rules; extend with verified CLS BBSC DBNO/QoL features | Source/real-game verification still required after adapting BBHost-specific hooks; don't reimplement released upstream features |
| Performance | Verified best frame times, memory, shader behavior, stability and transport latency on matching scenes/hardware | BBHost v0.2.25/#204 and v0.2.26/#210 merged upstream; the v0.2.27/#213 candidate is draft. No equivalent BBHost-vs-BBPort game benchmarks yet |
| Website/telemetry | Correct release/guide/account links, live online count only from verified game links; later Hunter's Dream-style features with user privacy | Never replace game-presence count with logged-in accounts or fabricate zeros; stage new telemetry safely, preserve Hosted=false |

## Release rules (all mandatory)

1. **Baseline preservation.** Freeze a working signed/verified bundle and a rollback path before experimentation. Do not replace production services or existing distribution links with untested branches.
2. **Same edition and protocol.** Enforce the compatibility policy of the actually distributed release. CLS v1.0.0 currently specifies that all members of one party use the **same client edition and release**; do not silently claim BBPort/BBHost mixed-party compatibility.
3. **Server parity.** Source+binary identity, existing database migration/backup, CSRF continuity, no hidden Hosted=true, full server staging and safe shutdown/reconnect.
4. **Real multiplayer.** Two independent Windows PCs first, then all five players (including join/leave/rejoin and different co-op/invader slot mixes); standard gameplay, bosses, events, death, travel, drops, saves and reconnect.
5. **P2P with real fallback.** NAT traversal, trusted peer grants and encrypted data for permitted channels, dedup/order/replay protection, no unsafe UDP packet forwarding, relay takeover under loss. Collect bandwidth/CPU metrics on the server.
6. **Client performance parity.** Same build, hardware, scene, driver, graphics settings and warm cache; report medians and p95/p99 frame-time, stutters, crash/recovery, CPU/GPU/VRAM and multi-hour soak. Do not substitute isolated synthetic plugin tests for real gameplay.
7. **One launcher/updater.** Install, engine selection, self-update, immutable package integrity, separate user data and saves, atomic rollback, changelog and reliable offline error handling. No game or account secrets in a release, CI, diagnostic report or GitHub.
8. **Whole product gate.** A release candidate consists of a compatible server version, client package(s), launcher/updater and documentation with exact immutable SHA-256 identities. No "ready" status until manual real-game acceptance and all release-contract gates pass.

## Immediate engineering sequence

1. **Maintain full-host source parity:** V419 and V420 plugin headers must be vendored into the real BBHost build. Verified V420 plugin+original YT UDP regression GitHub Actions #42222049521 PASS; full GUI/game-world integration is NOT verified.
2. **Complete V420 → real world consumer / NetSync:** V420 explicitly asks for original YT Snapshot and observes only epoch/last after encrypted transport. Next build a bounded complete snapshot+entries consumer with world epoch/lifecycle rollback, exact BBHost guest game hooks, proof that original save/game memory updates are correct, and eventually actual game traffic. No read-only metadata can grant writes.
3. **Evaluate BBHost v0.2.26 in a separate pinned candidate**: `bdc5cdf8be5f37188da9c2368e92be444fdc04cb`. Its P2P `src/hle/net.cpp` blob `0deb07fd11745aa8c8a80b550f93c7f81d99cff8` differs from v0.2.25 `476fd20eb8acf1acbb5ca45cbb4e03af6b6da4a2`. Existing V13/V19 packet-route instrumentation anchors *do not match* the newer send/split and receive/buffer code. Port those semantics explicitly, keep 0.2.24/0.2.25 baseline green, then prove game performance independently; never silently lift allowed source pins.
4. **Unify launcher and distribution** with a verified compatibility manifest and engine-specific settings/updates; keep the working BBPort route until BBHost works in actual YT multiplayer, not merely standalone.
5. **Integrate real five-player server/client and direct/relay** with staging and repeatable multi-client acceptance. Only then promote the pinned build, update site links and enable trustworthy live metrics.

## Released YT 1.4.0 adoption note (2026-11-06)

- Official v1.4.0 release at `efa0ad265d840d9195e55db2e3216f46f7daedd0` includes the formerly planned **1.3.2 five-hunter work**; v1.3.2 was never separately published. Avoid duplicating it.
- Prior original YT 1.3.1 SHA `5d2305ee611ef1e03be39ff925f0da75c9a70393` remains a pinned *fallback/transport comparison* for the existing source-only BBHost bridge, **not** the target public client release.
- Core protocol still declares `PROTOCOL_CURRENT=8`; a separate GitHub Actions gate compares four original reliable/Noise core files byte-identically between 1.3.1 and 1.4.0. Shared core source identity does not imply full game/client/protobuf compatibility.
- Prioritize released 1.4.0 team rules, five-hunter list/HUD, quick match, public server accounts, localization, co-op performance and bug fixes. Adapt to BBHost with per-feature acceptance; benchmark against actual BBPort rather than relying on upstream marketing measurements.
- Upstream PR #524 (Travel Together receive/send lock inversion) is **open** as reviewed on 2026-11-06: regression and platform-specific validation must pass before adopting, not an automatic patch to production.
- Original v1.4.0 release: https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/releases/tag/v1.4.0
- Tracking upstream merges/features must never silently upgrade the installed live Fornex service or shared account database.

## GitHub source-of-truth

- BBHost candidate integration: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/86
- BBPort/hybrid fallback research: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/85
- CLS: https://github.com/CLSAMG22/BBSC
- Latest released YT 1.4.0: https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together (1.3.1 fallback: https://github.com/lKaniel/bloodborne-server)
- BBHost upstream: https://github.com/droogie/bbhost
- Release candidate gates: `bbhost-track/full_release_contract_v400.json` and `bbhost-track/full_release_guard_v400.py`

**Status:** an engineering target with confirmed source-only components, not a finished five-player game or server/client/launcher release. Production Fornex and the active account database remain untouched by work in this branch.
