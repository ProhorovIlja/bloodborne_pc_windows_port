# Ultimate BBSC: one capability, one authority, evidence before replacement (V459)

Goal: **one BBHost-based Bloodborne client, one Yharnam Together world/game protocol, one coordinated launcher, one server-owned team state**. "Best of all repositories" does **not** mean running all candidate implementations together. Existing mechanisms must be inspected before porting anything. The machine-readable source-pinned baseline is [ultimate_capability_ownership_v459.json](ultimate_capability_ownership_v459.json), validated by [validate_ultimate_capabilities_v459.py](validate_ultimate_capabilities_v459.py) and CI `yt-ultimate-capability-gate-v459.yml`.

## A concrete decision for every imported patch

1. **Identify the exact responsibility and owner:** one writer per game-state, session, route, input-frameclock, settings key or persistent save namespace. Distinguish a transport adapter (BBHost UDP/NP) from a route/world authority (YT team/server). Reusing lower layers is not duplicate state ownership.
2. **Read both original implementations:** exact commit/release source, existing tests, documented behavior and callers. Inspect upstream forks/PRs *and* the current YT/BBHost code. File/feature naming is not enough to prove compatibility.
3. **Classify the candidate:**
   - **Preserve:** our implementation already matches/exceeds upstream on measurable correctness, latency and resources. Do not copy a duplicate.
   - **Repair:** patch a defect in the *existing* owner, as V455 fixes the BBHost/CLS `wanted_fps()` path. No second FPS limiter.
   - **Extend:** one owner gains a new opt-in capability, e.g. mod host-only events, new accessibility settings, or a five-player invasion admission rule with real game slots.
   - **Replace:** only if head-to-head performance/reliability/correctness wins; disable and remove the former implementation (or gate it behind a controlled rollback). Never run two writers concurrently.
   - **Reject/defer:** incompatible ABI, insecure identity, ambiguous save authority, copyright/license problems, measured regressions or unverified claims.
4. **Prove the migration:** single source of truth, exact before/after checks, negative replay/duplicate tests, actual game boot, Windows game sessions, 2–5 clients, NAT types, packet loss and 1h+ soak. Record p50/p95/p99 frame times, CPU/VRAM per client, p95 connection/RTT, relay Mbps/pps and CPU/memory per server, save recoverability and crash counts. A synthetic plugin test is *not* a multiplayer game test.
5. **Rollback without losing user data:** preserve signed packages, private game data, save compatibility and one authoritative persistence format. Revert by source-pinned owner switch, not by simultaneously running both options.

## Distinct layers: don't mistake similar names for duplicate implementations

| Actual function | Preserve as **one** selected authority | What other sources may add, not duplicate |
|---|---|---|
| UDP sockets, STUN | BBHost adapter (0.2.26 source; target wiring not game-tested) | libjuice ICE only if measured reachability is better **and** original discovery is replaced or cleanly delegated; do not create second peer socket per game |
| GameFrame route | YT authenticated team/server route | PR #85 signed, encrypted *eligible unreliable* direct route only after explicit game integration; reliable/ACK/world control still single server path |
| Member identity, invites, matchmaking | YT authenticated session and roster, with BBHost NP API as adapter | PR #217 signaling lifecycle only with API/server compatibility; no independent competing account IDs |
| Team state, bosses, flags | YT server-owned world log | Nightwatch/visy event bug fixes adapted to YT ownership; **never** run two HP/flag writers |
| Five-player group, death/DBNO, invasions | YT original team and game hooks | adapt visy two-invader admission/rewards to 5 slots *only after real game composition tests* |
| Vulkan graphics, shader pipeline | BBHost renderer and scheduler | adapt precise sampler lifetime, shader/cache regressions from deadinside, Lantern, Supermedo, shadPS4; never link a second renderer |
| FPS, input and timing | BBHost single frameclock | V455 repair existing online 60/120 cap; select Lantern/visy improvements only if frame p99 and input latency improve in exact scenes |
| Memory permissions | BBHost HLE mapping/protection via CLS adapter | V447 opt-in guest map-cache repair; no second independently updated memory mapping owner |
| Personal saves | game's native save through BBHost adapter | offline backup/recovery from Mrsuss/visy, preserving original save format and atomic restoration |
| Team-world saves | YT server world log | never mix with a second host-world progression database |
| Item trades | YT game/server transaction authority | visy gear+gems UX only after durable idempotency and no lost/duplicated items across crash or 90s+ ACK loss |
| Mod/event patches | YT event generator | Supermedo empty-event acceptance, visy mod compatibility fingerprint and host-only events as improvements to existing generator |
| Settings, updates, launcher | YT BLauncher as single UI, BBHost native settings adapter | transactional cache/profile updater and launcher QoL, **not** a second launcher or conflicting settings storage |
| HUD and spectating | YT game HUD | Nightwatch/visy QoL presented through existing widgets, not another duplicated overlay and polling loop |

### Specific trap to avoid: BBHost P2P vs YT server netcode

Original [BBHost online](https://github.com/droogie/bbhost/blob/bdc5cdf8be5f37188da9c2368e92be444fdc04cb/docs/online.md) documents UDP/STUN/relay for its own native NP P2P. Original [YT 1.4.0 netcode](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/blob/efa0ad265d840d9195e55db2e3216f46f7daedd0/docs/SERVER_COOP_PLAN.md) intentionally routes *all* game packets through one server UDP link and owns persistent team worlds. Our draft [PR #85](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/85) already contains authenticated Noise/signed-grant P2P building blocks. There is no basis to claim the real CLS BBHost game loader automatically connects these three as one system. The correct integration must identify the **actual game send/receive hook**, single channel/routing policy, coherent recipient/team/world epochs and no duplicate delivery, only then allow direct egress in real Windows game play.

### What V459 actually guarantees and does not

The Python gate rejects duplicate selected resource domains, unreviewed active alternative decisions, changes to pinned intended owner, missing original-source citations, floating pins, lack of measurable acceptance tests or rollback, and false claims of production/game success. It injects 10 adversarial invalid plans as regression tests. It does **not** scan all GitHub code, prove all runtime packets are single-routed, or test a game. Before promoting new patches, the actual CMake-linked source manifest and runtime packet/state traces must be reconciled against this register, and then subjected to game tests.

The independent **full Windows BBHost 0.2.26 + CLS YT 1.4.0 compilation** is ongoing as a separate gate. Keep the modern host FPS/renderer and original YT authoritatively owned control plane. Do not touch live Fornex, the website, game files, accounts, saves or the paused native-port track.

