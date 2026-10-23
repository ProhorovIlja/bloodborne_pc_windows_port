# Seamless Hunt: many-lobby matchmaking, hybrid P2P, and native Yharnam Together

Updated 2026-10-23. Existing Linux shadNet PoC running on Fornex is not to be modified yet.

## Confirmed upstream facts (pinned lKaniel/bloodborne-server at 77e350743a7cb4524cfcc1782fb6e3af64e25b15)

- server/src/server_link.h: SHLK Data/Coop/Rpc frames. UDP Data traffic is relayed by shadNet; LinkServer.cpp routes only members of a team and authorized channels. Every linked game uses a shadNet UDP server link.
- emulator/src/core/libraries/network/p2p_sockets.cpp already has UDP socket primitives and distinguishable game/control/coop packets. Reuse rather than duplicate them.
- server/coop/team_lobby.h: TeamSize=4, three guest slots. team_lobby.cpp GiveSigns: 7,6,5. Do not claim a fifth hunter works from changing one constant.
- Server authoritative world state remains on server in BloodborneWorld, even if peer game UDP packets move to P2P.
- Native Win64 BBPort uses a Python/Tkinter launcher frozen to BLauncher.exe, with bbport/launcher/bbport_coop.py hardcoded default ports. Our Windows one-click PoC already defaults its installer HostIPv4 to 199.195.193.131 and targets game port 32314/UDP, webapi 32315/TCP, backend 21443/TCP. Players should never type those by hand.

## Player experience (target)

Download installer -> automatically find own Bloodborne game, region/version/saves -> Seamless Hunt configured by default -> Play, Quick Play, Browse Lobbies or Private Room. Host can configure password, invasions (default OFF), scaling, Blood Level window and party size. Browser and Quick Play show available rooms for the same compatible protocol/game build. Many concurrent rooms, no 1-room-per-server limit. Failed joins should not permanently occupy capacity; use reservation TTL and atomic admission. No VPN, no need to run server at home.

Early build display: start character classification at 18 points in offensive stats (STR/SKL/BLT/ARC), infer Quality for STR+SKL, other two-stat hybrids; clarify this is a heuristic, not an immutable game class. Rich Presence optional and privacy gated: Blood Level, build, party size (and location only if opted in), never expose room passwords or peer IPs.

## Hybrid P2P split

Fornex **control plane**: authentication, public/private lobbies, Quick Play, host rules, version checks, world authority, server's Coop/Rpc channels, signaling and rendezvous.

Client **data plane**: large and high-frequency SHLK Data/game frames SHOULD travel direct peer-to-peer within a party when secure UDP traversal succeeds. Gameplay packets requiring server world validation still go via control path. Keep the current server relay fully operational as fallback.

1. Host creates a room on the server; host's choices are authorized server-side. Guests request atomic short-lived reservations, correct password/build/level/region, then confirm a member token. Never admit a fifth until gameplay runtime/protocol verified.
2. Connected peers authenticate via existing shadNet account/link credentials. Server observes actual UDP source addresses on 32314 and sends short-lived, authenticated scoped P2P candidates only among same-team peers. Do not trust self-reported third-party IP endpoints.
3. Both peers attempt simultaneous UDP hole punch on their existing sockets, with attempt budgets and a handshake binding: server-signed party+peer IDs+nonce+expiry+protocol version. Confirm bidirectional authenticated traffic; protect against replay, spoofing and direct IP privacy concerns.
4. Once verified, route selected game Data frames directly while server Coop/Rpc/world streams stay central. Preserve existing channel/interest filters from ServerLink::Hub::Routed / BloodborneWorld::RoutesPacket for both paths. Never send unauthenticated guest data into a game peer.
5. On packet loss, failed probes, topology changes, migration, or incompatible NAT, revert immediately to server-relayed Data with a monotonically increasing route epoch, deduplication, and reliable ordering. For symmetric NAT/CGNAT some parties will always need fallback.
6. Measure on VPS and clients: percentage direct/relayed packets, bytes/s per room, CPU time per forwarded MB, total rooms, P95 latency, loss, retransmission, and successful session joins. Also test recoveries, deaths, boss events, cross-area travel, and controller users. Require actual gameplay load tests before claiming CPU gains.

Security: experimental shadNet presently exposes HTTP game services with open account creation and no public audit. Use rate limits, authenticated API handlers, TLS at gateway, room-scoped reservation tokens, and never put passwords or session secrets into logs. Do not publish a localhost-only prototype directly.

## Implementation milestones and honest status

A standalone Python stdlib-only offline PoC (created as conversation artifact on 2026-10-23) implemented: multiple rooms, browsable public rooms, Quick Play, private hashed passwords, atomic reservations/TTL, host-authorized settings, version/level filtering, transport planning hints, 18-point build classification, opt-in Rich Presence metadata and local 127.0.0.1:32316 control API. **20 local tests pass**, including concurrent capacity reservations. This proves the matchmaking algorithms/API skeleton only: it is **not** integrated with native Qt shadNet, game lobby UI or game packets.

Before any public release:
- Port backend PoC into shadNet Qt6 WebApiRoutes with real authentication/SQLite persistence and compatible client menu.
- Implement/version P2P signaling and tested client data routing plus fallback in bbport/game's p2p_sockets.cpp and shadNet server_link protocol.
- Implement actual gameplay logic enforcing invasion/scaling options; lobby fields alone do nothing.
- Verify Linux server and the matched Windows CLIENT from same pinned source commit; do not mix unknown releases.
- Enable Discord Rich Presence only on opt-in, using live stats the game safely exposes.
- Separately reverse-engineer and validate a fifth native player slot/game UI/network protocol. Until proven, cap a room at four. Many simultaneous four-person rooms on a single VPS still work architecturally.

No changes to production CLS services, ports, firewall, DNS, or databases are authorized by this architecture document.
