# Seamless Hunt networking: Direct P2P first, authoritative server only when necessary

**Owner decision, 2026-10-25. This is a target architecture, NOT currently shipped.**
Do not ship a "one native server" that merely centralizes the same every-frame UDP traffic. One authoritative shadNet-based backend is intended for essential control, world/session persistence and relay fallback; **all provably safe, peer-directed gameplay frames** should bypass the VPS when a direct path exists. Native PC client and original Yharnam Together are the *only* targeted gameplay protocol. Preserve the user's working CLS/Fornex system until staged native parity/QA passes.

## Two independent design axes

- **Single server implementation**: Collapse BBSC Python HTTP :20443 into shadNet's native `BloodborneBackendServer` only after verified parity, consistent data migration and rollback. This reduces operational complexity, but does **not** inherently reduce UDP forwarding load.
- **P2P-first transport**: Explicit server-approved pair/session/epoch grants, both parties' permission and safe endpoint disclosure; NAT punch/ICE-like candidates; direct authenticated gameplay UDP and stream migration, leaving world/account/server-owned events on server, plus bounded fallback relay for incompatible NAT/firewalls. If the P2P gate fails, retain the working relay.

A five-player party would have up to 10 peer **pairs** in a full mesh, not connections from each member to the other 195 users registered on the VPS. Other topology (host-star, selected owners, hybrid) can be chosen **per game-channel and measured upload/RTT constraints** instead of forcing a mesh. Keep voice/presence/site state separated from gameplay and avoid periodic full roster pushes.

## Server control plane, low work per event

Keep account/session authentication, friends/blocks, lobby query, presence/heartbeat with bounded and aggregated updates, room invitation/co-op/invasion/duel eligibility, ban/rate-limit, version compatibility, session revoke, host election and migration, short-lived P2P candidate relay, current map/world/owner **authority** and durable progression decisions. The server does not need to simulate every player animation or transform every high-frequency peer packet. Avoid double-encoding or parsing native `SHAD` frames if already authorized for direct delivery.

Every activity above needs a measurable CPU/allocations/network budget, abuse policy, bounded history and graceful rejection under load. Async/nonblocking socket IO and batched SQLite writes should be tested in the *actual* Qt server rather than assumed faster. Site map/presence should publish summarized, privacy-safe events and not read the full game stream.

## Data-plane classification grounded in pinned shadNet

Original `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, `server/coop/packet_routes.h`:
- `NativeChannelPolicy::Pass`: direct candidate, if both belong to the authorized session and protocol/cryptographic/reliability guarantees hold.
- `NativeChannelPolicy::SameMap`: direct candidate **only** when current map/epoch and sender-to-target enemy ownership/hit direction are server-verified. This includes player movement 0x06, enemy positions 0x04, enemy HP 0x05, hit channel 0x14, animation/object/bullet traffic and other peer-forwarded channels, not just movement. Untrusted clients cannot self-certify map, enemy or team authority.
- `NativeChannelPolicy::Ours`: 0x2C personal/map items and 0x2F world corrections are server-managed, never direct offload.
- `NativeChannelPolicy::Drop`: 0x27 boss "thanks" kick is **discarded**, NOT rerouted as a regular game event. Never confuse "can't go Direct" with "must relay": dropped traffic should consume **neither** direct bandwidth nor unnecessary relay packets.
- Native game's `GameLink` uses unreliable channels 0..6 and reliable channels 7+, so moving 0x14/0x05/bullets to direct requires full stream handover (sequence, ACK, retransmit, ordering, duplicate suppression). No bypass based only on an open UDP socket.
- If one multiplexed native frame includes a forbidden subpacket, current safety gate keeps **the entire frame on the original controlled path**. Splitting/batching requires explicit tested native sequence/ack semantics before optimization.

Sources: `tools/poc/yharnam/hybrid-transport-v52/sh_channel_offload.hpp`, `sh_game_frame_offload.hpp`, `sh_direct_datagram.hpp`, `sh_direct_crypto.hpp`, `sh_direct_ingress.hpp`, `sh_hybrid_selector.hpp` in PR #17. Windows/Linux local socket/HMAC tests pass but these files are **not connected to live game sockets or authenticated server-issued grants**.

## Transport state and privacy

- Server validates same session, **role (host/guest/invader/duelist)**, target capacity, matching permissions, blocklist, current map/epoch, protocol revision and per-transport consent **before** disclosing peer candidates. Presence/search does not reveal private IPs.
- Mint short-lived grant with peer/server identity, direction keys generated from authenticated cryptographic material, expiration, epoch, stream identifiers, allowed roles and revocation generation. Client never trusts peer-supplied `server_verified=true` flags.
- Attempt simultaneous UDP punching using current Yharnam Together game socket; score IPv4/IPv6 candidate paths with observed RTT, loss and stability; keep direct only with verified remote packet MAC/replay checks; initial auth occurs over trusted server connection. For privacy-sensitive players offer a server-relay-only override. No automatic UPnP/router port exposure without explicit opt-in.
- Use authenticated encryption where required by privacy threat model; HMAC alone provides integrity but **not** confidentiality.
- Direct path drops mid-boss/death/host migration? Route switch must be coordinated, preserve exactly-once game effects where possible, avoid retransmission loss/duplicate events and return to relay immediately, not disconnect gameplay. Expired/revoked grants, new team/map epoch or changed consent force renegotiation.
- Reliable/owner mapping and per-user bandwidth/CPU ceilings are prerequisites. Direct gameplay may still be constrained by players' own Internet upload; measure peer bandwidth not just VPS egress.

## One multiplayer matchmaking service, many user controls

**One backend matchmaking/permission engine** handles:
- `Coop`: quick join, room browser, friends/invite, game-world bell shortcut.
- `Invasion`: quick find **only opted-in PvP worlds** with eligible slots and rules; optional targeted friend challenge/invite; in-game **Duel Bell can trigger the same intent**, but should not be the sole way to invade.
- `Duel`: accepted mutual challenge, friend/session browser, dedicated rule set.
- `Spectate`: session-granted role and camera controls, never an unauthorized peer attach or bypass for banned users.

Entry points (launcher UI, in-game menu, bell, friend list, quick match) should all submit the **same canonical intent** and obey the same server-enforced permission/capacity/blocklist/compatibility gates. A bell is a diegetic shortcut, not an independent network protocol. Co-op, Duel and Invasion have different **rules and consent semantics**, so identical UI entry points never imply identical access. Host may disable invasions without disabling friendly co-op. Invader cannot join a PvE-only room by knowing a direct IP/peer ticket or using a different button. A friend invitation is not equivalent to consenting to surprise hostile invasion. Spectator/free-camera authority must be explicit.

The Discord note about "Duels, death mechanic + spectate, 5 players, auto team-size difficulty" is an announced work-in-progress, **not** proof any of these exist in released source or the installed Fornex binary. Before pinning UI/keys, examine exact upstream merge and behavior. Five-player maximum and whether invader/spectator occupies one of those slots are open design questions; do not silently hardcode them across protocol.

## Non-negotiable performance and release validation

Report at baseline, Direct established and mixed NAT fallback:
- VPS CPU user/system, cores consumed, RSS, GC/allocator pressure, ingress/egress Mbps and packets/s, auth/login latency, friends search p95, room join success p95, per-game-channel relayed bytes, drop/reject counts;
- client net RTT p50/p95, loss/jitter, own upstream bytes/s, frametime p95, memory growth MB/h, crash/reconnect rates;
- sample 2/5/20/200 **total concurrent players across realistic party sizes**, observed ratios of direct/relay-only, restrictive NAT/CGNAT/IPv6 and packet-loss conditions;
- two PC online game tests: bells and matchmaking (coop/invasion/duel), account reuse, 5-player capacity only if shipped, death/DBNO/spectate, map transitions, boss/mob owner sync, saves and world restart, host migration, 2-hour sessions.

**No invented CPU/egress savings.** Target: shadNet gameplay-forwarding work falls sharply as directly connected peers increase; server still performs necessary state/auth tasks. In relay-only or CGNAT-heavy deployment CPU/egress can remain high; capacity must be load-tested with explicit operating limits, not promised as "200 players on any VPS".

## Current safety status

- Current live Fornex CLS server SHA256 `8b4b29b3e56414aa60bb53baa28285242b9a482e0a11e8dfe732ddc553094633` from 2026-10-25 friends archive is **already active**, unchanged by this branch. Python game backend at :20443 also remains operational.
- Real Direct P2P, NAT hole-punching, signed server grants and game-path integration are NOT shipped, regardless of isolated V52–V61 smoke tests.
- PR #17 Direct transport, PR #19 one-server/CLS inventory, PR #20 Windows FidelityFX compile fix remain separate and unmerged into production.
