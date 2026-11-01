# V240: first outbound GameFrame carrier bridge, real upstream YT structs

2026-11-01. Playable track, PR #85. This is an outbound integration
component **not yet installed into the YT client or server**. Never
describe this file alone as "Direct P2P online working".

## Verified upstream, pinned v1.3.1 source

- `server/coop/game_link.h` owns one `GameLinkPeer` per other member.
  `Send` assigns one sequence stream; `Flush` builds `GameFrame`, with
  `sender`, `instance`, `peer_instance`, `ack` and native entries.
  `Receive` handles unreliable per-channel dedup and reliable ACKs.
- `emulator/src/core/libraries/network/net_link.h` explicitly says the
  game's P2P datagrams go via one authenticated Noise NK *server* link.
  Thus YT 1.3.1 cannot be described as gameplay Direct P2P by default.
- `playable-track/hybrid_transport_policy_v1.h` and
  `hybrid_direct_ingress_v2.h` already gate movement channel 0x06 and
  receiver identity/instance, without authenticating peers or UDP.

## New component

`hybrid_direct_egress_v240.h` accepts **the real original `GameFrame`**,
a per-party server-authenticated `PeerRouteLease`, verified IDs/instances
and send callbacks. If authorization is absent, a secure direct-datagram
sender is not installed, or a frame is anything except one correctly
framed unreliable 0x06 player-state packet, it uses existing server link.

If `GameFrame::ack != 0`, it first sends an ACK-only frame along the
original server link and only then sends the movement frame directly,
with ack=0. On direct-send failure, the original frame, unchanged,
falls back to the server. Sender/instance/seq are never regenerated;
receiver uses existing shared `GameLinkPeer::Receive` for dedup.
Reliable/other channels are never sent direct.

`test_hybrid_direct_egress_v240.cpp` tests direct, ACK split,
unavailable-peer and failed-UDP fallback, stale lease, mismatched
identity, spoofed sender, mixed/reliable frames, invalid framing and
offline server, compiled against the published YT 1.3.1 source.

## Blocking work before it is safe to enable

1. Server signs short-lived ordered-pair/matching-world grants and
   revokes them on membership, hostility, map, host and instance change.
2. Establish real authenticated, encrypted UDP peer datagrams (e.g.
   vetted Noise or QUIC datagram machinery), with explicit key/session
   binding, replay protection, endpoint validation and NAT/STUN probes.
3. Wire `SendExistingGameFrameV240` into the **actual YT client send
   choke point**, with one `GameLinkPeer` per member shared between both
   carriers; `AcceptAuthenticatedDirectMovement` goes before the same
   receiver's `Receive`. Do not turn spoofable booleans into trust.
4. Check shadNet world/anti-abuse counters are not dependent on every
   player movement packet; keep a low-rate authoritative state heartbeat
   if needed. Verify ACK-only forwarding and fallback under loss and
   reordering on real sockets.
5. Run 2 and 5 client end-to-end tests across open/restricted/symmetric
   NAT, latency, rebind, disconnect, host transfer, late joining and
   combat. Track true server Mbps/CPU/p99 before opting in.

Only the original server link path must be enabled by default until
these gates are satisfied. No private binaries or Fornex changes.
