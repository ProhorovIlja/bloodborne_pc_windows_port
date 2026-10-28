# Seamless Hunt: one Yharnam Together game server and one native PC client

**Decision / 2026-10-25.** Final target: **one authoritative shadNet-based game-server process**, one compatible original Yharnam Together protocol, one native PC client/launcher, a single canonical account/friends/team/world identity, and **opt-in authenticated direct peer UDP** with relay fallback. No additional CLS, shadPS4, Supermedo or Awaken network protocols are targeted. Do not confuse independently useful repositories/design ideas with interoperability obligations.

**Current production is NOT yet that target.** Preserve production until in-game parity tests and data migration pass.

## Verified Fornex topology from deployment and original CLS source

| Listener | Current component | Purpose | Plan |
| --- | --- | --- | --- |
| TCP 31313 | `bbsc-shadnet.service` Qt `shadnet` | Legacy plain game protocol/account authentication | Keep protocol; secure Internet transport without breaking clients |
| UDP 31314 | same Qt `shadnet` | Link, matchmaking, currently relayed game frames | Remain indispensable rendezvous/world authority; opt-in Direct P2P for safe channels after authorization |
| TCP 31315 | same Qt `shadnet` | WebAPI, summoning/friends, matchmaking services | Keep in Qt game server |
| TCP 20443 | separate BBSC Python HTTP game backend | Bloodborne game online services and existing custom Python data/config | Replace with shadNet's built-in Qt HTTP backend **only after parity + data migration** |
| TCP 31320 | shadNet stats if enabled | Stats endpoint | Keep private/restrict access |

The current `shadnet.cfg` reported on Fornex has `BloodborneBackend=false`, `MakeAccountsAtSignIn=false`, `TcpLocalOnly=false`, `Host=0.0.0.0`; 31313 is **unencrypted plain TCP** on the public interface. Preserve account registration semantics; do not change these controls blindly. Authentication transport security and Internet rate limiting are release blockers.

**Proof an in-process 20443 backend exists:** CLS 2026-10-25 source tarball contains `src/bloodborne_backend_server.h/.cpp`, `src/bloodborne_backend.h/.cpp`. `src/main.cpp` constructs `BloodborneBackendServer` when `config.GetBackend().enabled`; `src/config.cpp` reads `BloodborneBackend` (default true), `BackendPort` (default 20443), `BackendFolder`, `BackendStore`, ghost/lantern TTL, etc. The supplied CLS script deliberately kept Python and forced `BloodborneBackend=false`, **not** because Qt lacks an HTTP backend. Its feature parity and live data format are not yet proven; do not claim two servers can be collapsed with a switch flip.

Web frontend/Caddy, databases and monitoring may remain separate *services* when useful. The architectural goal is **one authoritative multiplayer back end**, not the impossible constraint that every network service must share a single port or operating-system process.

## Source of truth and deployment evidence

- Pinned native Yharnam Together baseline `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`. The upstream `main` was observed at `f34b82dd0a6e9efe6c44f101debc2585a2ef36d8` on 2026-10-25, **not yet imported or compatibility-vetted**.
- CLS handoff: `server_linuz.zip` (2026-10-25); original ZIP SHA-256 `6a557aa580bbc2883e6d122601aa2bfda4f1de09846f374fe4a25e49c7d001b7`, inner original `amanises-yt-public-server-src-20261025.tar.gz` SHA-256 `ade8fc9baa46ea47f4122ae723fcabc7406e0e2ba6b33925d81cf9502b5c772d`. Author attribution: CLS_AMG/Amanises; README credits Yharnam Together, AMANISES and Supermedo; retain SPDX and credits. This branch contains an **integration inventory**, not the binary original third-party ZIP. Retrieve the actual archive from the user's uploaded Project source, not a synthetic GitHub download.
- Original CLS README: Friends search, request, accept, decline, cancel, removal; list indicates online/hunt/team; same shadNet friendship table, new client required for UI. Old client expected to play, but no field QA evidence yet.
- Fornex `BUILD_AND_TESTS_PASS` and `STAGE_AND_HASH_PASS` candidate SHA-256 `8b4b29b3e56414aa60bb53baa28285242b9a482e0a11e8dfe732ddc553094633`; `GUARDED_DEPLOY.sh` returned `LIVE_UPGRADE_OK`; `/opt/bbsc/shadnet/shadnet` and `/proc/1031155/exe` SHA matched. After install `bbsc-shadnet.service` was active and game clients authenticated and made world/summon calls.
- Live rollback snapshot: `/opt/bbsc/backups/friends-20261025-20261025T130156Z-1031121`. Do not expose DB contents, passwords, tokens, IP-based logs, game assets or user PII in this public repository.
- V60–V61 isolated Direct UDP crypto/socket tests passed both OSes: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40138658623. **Not** integrated into real client or Fornex gameplay. Windows native game renderer build **FAILED**: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40133678320 (AMD FidelityFX 1.1.4 frame interpolation uses MSVC-only `_countof` under CLANG64). Isolated fix and fast Windows real compiler smoke on https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/20; this does **not** yet prove the entire Windows game builds.

## Migration gate: Python 20443 -> native Qt 20443

1. **Inventory without interruption:** inspect the *actual* service unit, Python entrypoint, existing backend file/database paths, game URL overrides, Caddy reverse proxies, external clients and timeout policy. Record request method/path and response schemas, excluding secrets. Keep current live unchanged.
2. **Functional contract comparison:** compare Python handlers to `src/bloodborne_backend.cpp` and `src/bloodborne_backend_server.cpp`; cover `ss.info`, guest login/bootstrap, lanterns, ghosts, tombs, summon polling, notice/broadcast, chalices, game saves and customization. Unit tests and replay captures must assert response status/body and persistence semantics.
3. **Data migration:** identify both stores; do not reuse a Python SQLite/file store blindly as Qt's `BackendStore` unless schema and writer have been verified. Create a consistent offline snapshot, transform only if necessary, validate per-record counts and referential consistency, and prepare reverse migration/rollback policy. Account/friend relationships remain authoritative in shadNet's `db/shadnet.db`.
4. **Isolated integrated candidate:** run Qt shadNet with its own clone of config/database and **non-live** `Host=127.0.0.1`, e.g. `32313`, `32314`, `32315`, `32443`, isolated backend storage. Configure `BloodborneBackend=true` **only in staging**; verify it actually binds 32443 and passes game HTTP/JSON parity tests. Ensure staged clients target the alternate ports; never point real clients to the staging database.
5. **End-to-end QA:** identical player account/login, friends, duel permissions, team formation, map state, boss/death/respawn/spectate, 5-player claim only after upstream code exists, reconnects, 2-hour soak; test with current and new game clients and server restart. Validate site/presence consumers and load on 2- and 200-player scenarios.
6. **Coordinated cutover with rollback:** notify players of maintenance, take transaction-consistent snapshot, stop Python cleanly, confirm 20443 vacant, deploy vetted Qt config, restart shadNet, verify port/path/health and a real game session, then observe. If failed, revert Qt config and start Python using preserved data. No automated production switch in this branch.
7. **Only when parity + rollback are proven:** disable the separate BBSC Python game service permanently. Keep optional reverse proxy/site outside the game server as needed.

## Direct P2P vs server capacity

A single shadNet process with two hundred clients all relaying every gameplay datagram still incurs traffic and CPU scaling. In final design server stays responsible for accounts, matchmaking, session/consent grants, team/map/world authoritative events, anti-abuse, presence and relay when necessary. Peer-directed gameplay can go straight over encrypted/authenticated UDP **only after** secure grants, NAT rendezvous, shared world-channel authorization and reliability migration are complete. Mixed server-owned packets stay on server. CPU improvements must be **measured**; never assert P2P is deployed based on isolated unit/loopback tests.

## New roadmap from developers' Discord, 2026-10-25 (announced, not shipped)

A Kaniel message describes work toward duels, death mechanic + spectate, five-player teams, expanded death penalties, automatic difficulty scaled by team size, server optimization/security, bot protection, rate limits and **experimental** Google/Discord login. CLS says server friends are done and awaiting on-server test. These are **announcements**, not proof those features are in current installed executables or the pinned baseline.

The phrase "your death mechanic + spectate" plausibly refers to the proposed Down But Not Out recovery and spectating, but the screenshot **does not confirm** a host-selectable on/off toggle, precise lamp/boss respawn rules, F/F1 camera controls, freecam or player-switch keys. Keep such behavior as proposed settings pending verified code and team agreement. When upstream pushes changes, review its exact commit and license, compare against CLS additions, then selectively port and test instead of overwriting a live custom server.

## Immediate next engineering work

- Validate changed functions and conflicts against CLS snapshot, original pinned Yharnam Together and new upstream commits.
- Implement a **read-only** Fornex service/route inventory for migration; no default deployment, no credential disclosure.
- Build backend parity tests and isolated Qt HTTP port 32443 staging; do not remove Python until release gates pass.
- Continue native Windows artifact and Direct P2P integration in separate branches, not by merging unfinished work into live production.
