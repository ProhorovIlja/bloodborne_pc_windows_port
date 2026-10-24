# Bloodborne native port | Security, anti-cheat, PvP privacy and full-stack audit
Date: 2026-10-24. Branch: feature/yharnam-dedicated-server-poc
Pinned upstream: lKaniel/bloodborne-server @ 77e350743a7cb4524cfcc1782fb6e3af64e25b15.

STATUS: SOURCE AUDIT IN PROGRESS. No trusted public PvP, no full Windows build and no production server rollout.

## V25–V27 follow-up: authenticated rooms, inbound work, and endpoint cleanup

The pinned source contains three independent integrity gaps:

- **V25 (source integrated; runtime not verified):** `server/src/server_link.cpp` accepts a logged-in transport ID, while `server/src/bloodborne_world.cpp` separately accepts client-supplied `Hello.member` and `LobbyHello.member`. New strict mode `SH_STRICT_MEMBER_ID_BINDING=1` checks both claims against the lower-hex representation of the transport ID (matching `BoardMemberOfOnlineId`). In strict mode, a missing `ServerLink::SignIn` callback now rejects *all* links. Strict mode is **off by default** to preserve older PS4/BBPort clients. This check does not prove that SignIn itself is cryptographically sound.
- **V26 (source integrated; runtime not verified):** `Service::Receive` can otherwise decode arbitrarily many complete, small protobuf messages after V24's per-message cap. Strict-mode-only, O(1) per-linked-client quotas now check message count and byte volume **before protobuf decoding** (initial burst 240 messages / 16 MiB; refill 120/s / roughly 4 MiB/s). Rejections are logged sparingly, with no auto-bans. Test with real map joins and catch-up before enabling: these are preliminary thresholds, not production-proven.
- **V27 (source integrated; runtime not verified):** a `ServerLink::Hub::OnHello` on the **same endpoint** changing its online ID overwrote `virtual_endpoint` without retiring the old `by_virtual` and pair routes. V27 first tells prior teammates it departed, calls `Unlink`, and reports `result.gone` so the previous world is forgotten. It also records `retired_online_ids` and removes their matchmaking `udpExt` mapping in `LinkServer::Apply` **before** registering the new link. Repeating Hello with the same identity remains uninterrupted.

Independent portable C++20 policy tests for V25, V26 and V27 compiled with `-Wall -Wextra -Wpedantic -Werror -fsanitize=undefined` and passed locally. This is **not** a full Qt integration test. Tests and immutable source-anchor checks were added to the workflow, but no successful GitHub Actions workflow run or full Windows client build is confirmed. The production Fornex/CLS server remains untouched.

**Unresolved high-priority risks:** transport Hello/sign-in rate limiting occurs *before* the co-op ingress quota and can incur password-hash/DB work; lower game-link fragments and held out-of-order frames need their own resource limits; bounded per-IP/account connection quotas and safe cleanup of all stale matchmaking entries on normal disconnect; server-issued verified roles and packet filtering for private PvP metadata; server-authoritative gameplay economy and inventory validation; startup cheat checks before joining; signed launcher update metadata. The source-level strict identity check alone is not strong anti-cheat.

## Non-negotiable product rules

1. A hunter may use local character tools when offline OR online but not in a team, invasion, or live co-op session.
2. Joining a group or an invasion session disables client-side changes to blood echoes, insight, items and stats, and requires a clean runtime without startup gameplay cheat patches. This must be enforced by the new client and verified by server-owned gameplay rules where technically possible.
3. Default group = Fair Play. Optional private sandbox could permit agreed custom behavior, but no UI-only 'host permits cheats' checkbox must pretend to enforce modified clients.
4. Ordinary PvE crossplay with old PS4, BBPort and CLS clients should remain available on its compatible legacy protocol. Strong PvP integrity requires negotiated new protocol and must not silently downgrade to a leaking client.
5. Same-side hunters see their co-op allies on HUD/map/compass. Same-side multiple invaders see each other in these feeds. Opposing teams do not receive exact map/compass/party-vitals metadata. A server-verified spotting event can eventually show a brief, coarse last-seen marker; never an enemy wallhack. Normal in-world game actors require separately tested PVS/LOS replication. Restrict PvP death freecam to avoid ghosting.
6. Never touch the established Fornex/CLS production daemon or ports during development, and preserve the last good client for rollback.

## Confirmed code findings

| Area | Severity | Pinned-source evidence | Current mitigation |
| --- | --- | --- | --- |
| Server vitals | Medium | server/src/bloodborne_party_boards.cpp added uint32 revive damages without overflow protection | V22 saturates counters and checks bounded inbound vitals |
| Server trust | Medium | bloodborne_world.cpp accepted client-reported HP/position and overly long identity strings | V22 cheap per-report plausibility and length checks, sparse logs, no bans |
| Server/client network | High | server/coop/coop_stream.h appended arbitrary non-final fragment sequences to partial without a size cap | V24 8 MiB per-peer reassembly cap; reject oversized messages through the final fragment |
| Client cheats | High for fair sessions | Save editor directly writes client-local game data; startup cheat patches can persist after UI switches are changed | V21 session-aware local editor block. Clean-runtime admission / server verification STILL TODO |
| PvP information | High privacy risk in future PvP | coop.proto 7 / composed 8 lacks authoritative host-vs-invader role and permission fields; current boards are team-oriented | V23 fail-closed, testable faction privacy *policy only*, NOT wired |
| Server world storage | Needs investigation | bloodborne_world.cpp reads world/journal/trades files with readAll; growth/bounds require workload analysis | TODO: storage quotas and corruption fuzz |
| Network packet routing | Needs investigation | coop/packet_routes.h deliberately passes some frames with unknown maps for PvE join | TODO: strict versioned PvP metadata/actor routing; preserve PvE join |
| Identity binding | High potential risk | OnHello uses self-claimed hello.member/hello.host; network online_id exists but binding and authentication not yet established by audit | TODO: verify server-link identity, bind claims to authenticated principal for strict rooms |
| Launcher updates | Supply chain review | release update code checks SHA-256, but cryptographic source/authentication of manifest needs review | TODO: signed manifest / verified artifact pipeline |
| GPU map resources | Medium | 3D-map and texture-cache lifetime, chart CPU map cache and malformed archive reads | Source V16–V20; full GPU/device-loss stress and native Windows build still TODO |

These are source-derived observations, not claims that any particular reported crash, cheat incident or malicious exploit has happened.

## Lightweight server defense design

- Protocol-driven validation at packet ingress, with per-room and per-player caps, rather than scanning client RAM or running kernel anti-cheat.
- Bounded reliable-fragment buffers, message sizes and connection counts. Rate controls use O(1) token buckets per authenticated peer, with a small bounded map and time-to-live, not unbounded logs.
- Player/host identity must be bound to a verified transport principal; a self-claimed display name or host=true bit is not authentication.
- Use authoritative room membership, factions, PvP roles, world-event ordering, relevant inventory/trade operations and server-observable violations. Never trust client-proclaimed line of sight or inventory balances as proof.
- Use anomaly scores with evidence, reconnect tolerances and human-review actions first; avoid irreversible auto-bans for lag, legitimate teleports, level-up or modded-but-private saves.
- No portable userspace client anti-cheat can guarantee a modified offline PC game client is clean. For public 'trusted' groups, independent server-owned progression checks and a narrower mode with negotiated, controlled clients will be required.

## Planned audited surface, not yet complete

Priority 0: stream/parser memory caps, peer authentication, replay, quotas and server stability.
Priority 1: session rules/cheat admission, role-authoritative privacy filtering, crossplay gating.
Priority 2: game-side hooks/patch conflicts, save rollback and startup cheat state checks.
Priority 3: Qt/PowerShell/Python launcher updates, installer paths, signed releases and network setup.
Priority 4: Vulkan lifetime, map thread and cache bounds, long-play performance and full Windows source build.
Priority 5: gameplay/UI spectators/invasions, death flow, map reveal fairness and user experience.

## Release gate

- Rebuild game, launcher, Linux game-link server from the pinned exact sources; run CTest/Python suites and apply code transforms with fail-closed anchors.
- Fuzz message sequences: missing LastChunk forever; oversize length; malformed proto; reconnect during partial; duplicate IDs; replay; flood; 2v2 invasions; host migration; false reports.
- Test old protocol 7/8 PvE co-op on PS4/BBPort/shadPS4 clients separately from new PvP. Reject unsupported PvP clients, never silently downgrade private telemetry.
- Stress 45–90min with 4+ peers, relay throughput, CPU, RSS, VRAM, GC and scheduler delays; test clean rollback.
- GitHub Actions workflow run and full Windows compile are not yet confirmed; production CLS/Fornex unchanged.

Implementation:
- tools/poc/yharnam/server-trust-v22/
- tools/poc/yharnam/pvp-privacy-v23/
- tools/poc/yharnam/stream-bounds-v24/
- tools/poc/yharnam/unified-v9/compose_sources.py

## V28 update: cheap Hello admission before password database (source-only)

Confirmed: `server/src/server_link.cpp` called an optional authentication callback on every parsed Hello; the actual `LinkServer::SignIn` callback may invoke the account database and password KDF for previously unseen account IDs. Earlier V26 quotas applied only to *completed co-op protobuf messages*, too late to protect the authentication path.

V28 inserts an **opt-in** fixed-memory per-IP and global token budget immediately after decoding Hello and before `SignIn`. The initial limits are 8 per-IP burst at 2/s and 24 global burst at 6/s. A four-way hash table contains at most 8192 address slots with 30-second idle reuse; there are no background timers, per-request heap allocations or automatic bans. Environment variable: `SH_LOGIN_ADMISSION=1`. If disabled, existing legacy behavior is preserved. Rejected Hellos receive no refusal so clients can retry, and the default remains **OFF** until stress testing confirms suitable caps.

The native C++20 policy test and five local Python transform tests passed; the C++ test also passed under UndefinedBehaviorSanitizer, including address collisions and extreme time values. A **new GitHub Actions workflow** `.github/workflows/shyt-v28-native-server-build.yml` was added to compile the actual pinned Qt/Linux server and Qt networking/world tests, but **no successful workflow run has been observed**. Draft PR #2 was opened for review and CI without merging. No production Fornex deployment.

**Still required:** per-IP/total admission tuning under real NAT connections and login storms, bounds on account-sign-in cache and RPC pending buffer, full Qt test results, signed/verified identities, and signed release pipeline. This protects server CPU but does not prevent volumetric traffic or a botnet starving valid logins.

## V29 follow-up: finite RPC buffers and credential cache (2026-10-24)

The pinned server's `LinkServer::OnRpc` appended bytes indefinitely to `RpcEnd.pending` while its local backend socket was not connected; even a connected `QTcpSocket` could accumulate queued output via `write` without checking `bytesToWrite`. Long-lived `m_signedIn` accumulated cached successful account hashes without an eviction policy.

V29 introduces a 2 MiB backpressure limit for pending RPC and queued Qt TCP writes; it checks BEFORE constructing the copied QByteArray, closes over-budget sockets and refuses more data for that tunnel until a new `Opened` event. The successful credential hash cache is limited to 2048 entries; an evicted account is authenticated again using the normal database path. No new threads or timers.

V29 was integrated into the V3–V29 compositor, the native Qt build workflow and source-safety CI. Isolated **5/5 Python tests** and a C++20 standalone unit with `-Wall -Wextra -Wpedantic -Werror -fsanitize=undefined` passed locally; source patch anchors were each verified against exactly one occurrence in the pinned server. Qt game-link server and real cross-client sessions are **not compiled/tested yet** in the present environment. The 2 MiB queue and 2048 account thresholds are provisional. Full load tests and cache invalidation after credential rotation remain open.

Implementation: `tools/poc/yharnam/rpc-budget-v29/`.


## V30: verified live account status on cached reauthentication

**Confirmed security flaw:** On a hot `LinkServer::SignIn` cache hit, the source compared `SHA256(client_secret)` against a persistent in-memory hash without checking `Database`. The V29 cache-size bound did not remove this vulnerability. A prior successful login could therefore keep accepting credentials which had since been changed or an account which had been banned/deleted, until its cache entry disappeared.

V30 changes cached auth entries to hold two stamps: the cached SHA-256 client secret and the salted password hash returned by the authoritative SQLite account record at sign-in. Every cached reauthentication does a **cheap indexed** `SELECT username,hash,banned` (no 100,000-round password KDF). Banned, deleted, inaccessible or invalid database rows fail closed. A changed password hash removes the old cache entry and falls back to normal DB verification of the newly supplied secret. Cached unchanged accounts with a wrong secret are immediately refused without password KDF. Newly verified banned accounts are refused too. Existing V29 2048-entry eviction still applies.

The branch includes portable C++20 policy tests, pinned-source Python transform tests, and a new real Qt/SQLite account regression in `server/tests/test_accounts.cpp` exercising ban, hash change and deletion. The native Qt-server workflow now builds/runs `test_accounts` alongside `test_server_link` and `test_bloodborne_world`. The portable C++20 test passed locally with strict warnings and UndefinedBehaviorSanitizer. **Qt/SQLite integration is not verified until a workflow or equivalent build actually runs.**

Note: this corrects **new login decisions**, not instantaneous expulsion of already connected sessions. Server-initiated session revocation after an admin ban still needs a proper authenticated control channel. The current UDP Hello secret is not itself encrypted; future public service should add a secure transport or secure admission handshake.

Implementation: `tools/poc/yharnam/auth-revocation-v30/`. Working Fornex/CLS not modified.
