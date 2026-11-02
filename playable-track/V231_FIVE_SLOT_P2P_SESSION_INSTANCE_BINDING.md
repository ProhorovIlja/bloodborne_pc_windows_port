# V231: fail-closed Yharnam Together P2P lease after five-slot reuse

Date: 2026-11-01. Source-only experimental PR #85, not a public
hybrid Direct P2P release. The Yharnam Together latest release is still
v1.3.1 (2026-10-31), and upstream five-seats/rig PRs #484/#486
are **still Draft** at the time of this check. No shipping server
or Fornex change was performed.

## Concrete source-prototype vulnerability

Previously `PeerRouteLease` matched only the ordered pair of hunter
IDs and a world epoch. A restarted party, rejoined hunter or a fifth
slot occupied by another instance could reuse the same displayed
account/member ID while the server-issued session had changed.
It was possible for an apparently matching old lease to authorize
DirectPeer selection despite that identity ambiguity.

## Changed policy and ingress checks

Added a **server-issued party-session identifier** and the
**exact authorized sender and receiver instance IDs** to
`PeerRouteLease`. `ChooseNativePacketCarrier` now refuses
DirectPeer unless all three fields are present, in addition to
existing epoch, player opt-in, authenticated route, same map, probe
freshness, channel-0x06-only and nonhostile constraints.

`DirectIngressIdentity` now also contains the authenticated
party-session ID. `AcceptAuthenticatedDirectMovement` rejects
a direct frame whose authoritative party-session differs or whose
ordered sender/receiver instance IDs do not match the lease, even
if the same hunter display IDs and map are reused. All older
reliable channels and story/flags/party events remain on Server.

New negative tests cover:
- missing party-session ID, sender instance, receiver instance;
- a replayed earlier team-session token with reused hunter IDs;
- fifth-seat or join/restart instance reuse for either participant;
- existing cross-carrier GameLinkPeer deduplication and failover.

Public CI compiled and ran with the pinned original YT v1.3.1
GameFrame/GameLinkPeer/packet routing types. **SUCCESS:**
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41332024104

## Security and functionality not yet demonstrated

These are only **source-structure and ingress policy constraints**.
They do NOT issue or cryptographically sign server leases, implement
UDP handshakes, NAT traversal, endpoint rebinding, session keys,
packet authentication/replay limits, or full native 5-hunter gameplay.
The authority/team/instance IDs must be obtained only via the
authenticated original game-server channel, not peer-supplied UDP.

A shipping implementation must verify dynamic team creation,
fifth-slot reuse, real two-PC and single-PC multi-instance joins,
Hunter's Dream visibility, DBNO, invasion mixes and network load
before enabling direct traffic. Do not import upstream Draft PR
#484/#486 into production without their complete cross-component
gameplay and dedicated-server rig tests.
