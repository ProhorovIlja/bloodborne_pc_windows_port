# Seamless Hunt: cooperative interoperability and migration policy

**Status: proof of concept, not a released global online service.**

Seamless Hunt is an experimental community client/server downstream of
[Yharnam Together](https://github.com/lKaniel/bloodborne-server). It is
intended to improve game stability, accessibility and long-session co-op
without requiring players to abandon an existing community server or client.
Our Fornex target is **Ubuntu 24.04 / Qt 6.8.3**; its live production services
and database are **off limits** to development build deployment.

## Independent work, design inspiration and copied code are different

Different Bloodborne projects solve similar gameplay problems. A shared goal
(such as seamless sessions, surviving boss kills or a spectator camera) is
**not, by itself, proof of source-code copying**. Conversely, code displayed
publicly on GitHub is **not automatically licensed for redistribution**.

At this stage, no independent audit of source-code copying allegations
between [Visy](https://github.com/visy/bloodborne_pc_windows_port),
[Nightwatch Co-op](https://github.com/vladtepes22/NightwatchCoop),
[LukeYui's Elden Ring Seamless Co-op](https://www.nexusmods.com/eldenring/mods/510),
[CLS BBSC](https://github.com/CLSAMG22/BBSC) and other teams has been
completed. **Do not claim that a project stole code or that a competitor is
unplayable without reproducible, attributable evidence.**

What the public source documentation actually indicates:

| Project | Publicly documented approach | Status in **our** mainline |
| --- | --- | --- |
| **Yharnam Together** | Native Bloodborne PC with its own party co-op system, Qt shadNet and BLauncher; explicitly credits LukeYui for design *ideas*, not copied code | **Only pinned game, launcher and server baseline** (`77e350743a7c...`) |
| **CLS BBSC** | Seamless-co-op mod for the shadPS4/shadp2p networking family; independent game-server and account protocol | **Interoperability goal**, not demonstrated binary/network compatibility with the Yharnam Together party implementation |
| **Visy native Windows port** | Independently implemented serverless direct-party co-op; README describes Elden Ring Seamless Co-op as the design model | **Research/reference only**; its renderer, fixes or networking modules are not silently merged into this mainline |
| **Nightwatch Co-op** | Its own README states a modified Awaken/Lantern Engine with Visy's co-op integration; GPLv3 with extra attribution obligations from Lantern Engine NOTICE | **Research/reference only**; no included Nightwatch or proprietary engine assets |
| **Elden Ring Seamless Co-op by LukeYui** | Original Elden Ring gameplay mod and common design inspiration for other titles | **Ideas only** in the credited Yharnam Together lineage; we make no claim of imported ERSC source |

We do **not** rank these projects as 'garbage', 'the only real co-op', or
'perfectly stable'. Their public claims have varying testing coverage. We
assess feature reliability with two real PCs, logs, latency simulation,
regression tests, crashes and save checks rather than promotional percentages.

See [CREDITS.md](../CREDITS.md),
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) and
[CONTRIBUTING.md](../CONTRIBUTING.md) for source rights and attribution.

## No forced migration or fabricated cross-play

**Different online protocols do not become compatible because their clients
share a game executable, shadNet name, UI design or server host.** No
'cross-play confirmed' badge, cross-realm player count or invitation link
may be shown for a pair of clients until an instrumented two-sided test
confirms account sign-in, matchmaking, reliable game packets, privacy of
passwords, death/revive and safe disconnect.

Our compatibility tests must distinguish all four layers:

1. **Client runtime:** native Yharnam Together, PS4/CLS, shadPS4/CLS,
   legacy BBPort, Visy/Nightwatch engine: version, patch sites, build and
   gameplay hooks differ.
2. **Discovery and authentication:** host address, sign-in provider,
   account namespaces, version negotiation, password/private-party
   isolation and public listing rules. Never copy credentials between
   unrelated providers.
3. **Game session transport:** distinct message/packet schemas,
   encryption, reliable send, lobby membership and game events. A
   proxy cannot safely translate these without a reviewed adapter.
4. **Game/world semantics:** door flags, NPC summons, items, quest
   progress, regions, deaths, boss ownership and save-state lifecycle
   must agree on *both* sides.

**Default behavior:** use the pinned Yharnam Together co-op as documented
for a single compatible party, and keep the existing production CLS realm
unmodified. Do not expose a fake global player pool.

## ShadNet transport and minimal server bandwidth

Pinned Yharnam Together's **team network mode is server-relayed UDP**:
gameplay datagrams pass through shadNet, which also owns the shared world.
See upstream [SERVER_COOP_PLAN.md](https://github.com/lKaniel/bloodborne-server/blob/77e350743a7cb4524cfcc1782fb6e3af64e25b15/docs/SERVER_COOP_PLAN.md).
This differs from early direct-P2P architecture and from CLS's network
transport. The current client/server build **does not guarantee direct
P2P or a low relay bandwidth bill**.

The target of low server load is legitimate, but **direct game-data P2P
is a future compatibility-reviewed design**, not a switch to toggle.
Safely offloading peer packets requires NAT traversal, capability
negotiation, game-world authority, privacy/consent to reveal endpoints,
reliable fallback relay, join/leave handling and validated game events.
Server-side world and lobby messages cannot vanish just because movement
uses P2P.

For capacity planning, use the tested, assumption-only
[`game_traffic_capacity.py`](../tools/diagnostics/game_traffic_capacity.py)
to estimate the `N - 1` relay fanout in rooms of N hunters. It does NOT
measure real game bandwidth, server memory, CPU or network latency. **All
publication claims must follow instrumented two-PC and Fornex staging
tests**, including adverse packet loss/jitter.

## Compatible provider selection, not vendor lock-in

A future launcher can present an **explicit, opt-in** list of supported
co-op services once those services have been implemented and tested.
One active provider per play session; each provider must expose its
own independent configuration, protocol version and health checks.
The UI must say `Not supported` instead of pretending any two backends
are interchangeable. Never silently change a working player's endpoint,
overwrite their credential cache, rewrite a save or redirect existing
players when a fork releases an update.

It is acceptable for players to remain in their existing communities.
The portal may show independently verified, **consented and aggregated**
counts by provider when data is authorized and sourced. No scraping
personal account lists, passwords or another community's private
online service. We must not claim that an external community endorses
Seamless Hunt.

## When a better maintained implementation arrives

We want an **exit strategy**, not indefinite ecosystem fragmentation.
Replacing the test-only co-op code on Fornex should follow this order:

1. Obtain and validate the new project's license, author notice and
   corresponding-source requirements before any integration.
2. Capture immutable build/version/protocol identifiers; measure server
   compatibility and evaluate whether new code can genuinely re-use
   existing accounts and network sessions.
3. **Back up** the staging database/configuration and test on isolated
   staging ports and disposable test accounts, preserving live Fornex.
4. Provide an opt-in launcher update with clear game-mode and server
   selection; do not migrate passwords or saves unless players explicitly
   approve and a verified import/rollback exists.
5. Test mixed old/new clients, hosting and guest gameplay, NPC signs and
   doors, boss state, latency, loss, NAT/VPN reachability, graceful
   disconnect and at least one sustained real two-PC session.
6. Publish original author credits, full licenses and source availability.
   Only after independent testing should the maintainer approve a
   production cutover. Preserve a reversible path for those who remain
   on the old client.

A failed migration leaves the original working realm and saves untouched.
The temporary Seamless Hunt experiment is not an excuse to degrade another
team's work, nor is it a requirement that communities merge.

## Release blockers

At present, all cross-client CLS/PS4/shadPS4 interoperability and a public
multi-client realm remain **unverified**. 'Can compile' and 'can connect to
one local host' are separate from a tested globally compatible service.
The original `master` Windows port is not this project's current
engine/launcher. No official authorization from external teams is implied.
