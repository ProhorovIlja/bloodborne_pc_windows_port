# Bloodborne native port | Security, anti-cheat, PvP privacy and full-stack audit
Date: 2026-10-24. Branch: feature/yharnam-dedicated-server-poc
Pinned upstream: lKaniel/bloodborne-server @ 77e350743a7cb4524cfcc1782fb6e3af64e25b15.

STATUS: SOURCE AUDIT IN PROGRESS. No trusted public PvP, no full Windows build and no production server rollout.

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
