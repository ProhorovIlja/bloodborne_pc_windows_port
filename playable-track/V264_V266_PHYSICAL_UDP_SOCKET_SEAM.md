# V264–V266: real YT physical UDP socket source integration

Date: 2026-11-01. Playable Draft PR #85.
**NOT enabled in the shipping client. No Fornex or retail game changes.**

Pinned Yharnam Together 1.3.1 commit:
`5d2305ee611ef1e03be39ff925f0da75c9a70393`.
Original `emulator/src/core/libraries/network/p2p_sockets.cpp` blob:
`087aef46868b55320f139b3f7c4f46e5fc545347`.

## Concrete source changes

`apply_yt_direct_physical_v265.py` applies after V256 to a
**disposable original YT source checkout**. Exact original Git SHA,
source blob and 10 unique source anchors are checked before patching.

The actual `P2PTransport` then gains an independently typed physical
movement path, not a replacement for the server's shadNet protocol:

- `SendVerifiedMovement` uses the **existing** physical OS UDP
  `host_socket` and original `Transmit` method, bypassing the
  server-wrapped `SendFrame` only for an authorized encrypted SHDP
  movement datagram. No additional port, network thread or polling loop.
- `ReceiveMain` recognizes exactly the 9-byte SHDP v1 magic
  `FF FF FF FF S H D P 01` and verifies a previously authorized
  source endpoint + expiry. It never forwards it to standard original
  `Link::TakesDatagramFrom` / `Deliver` or native game sockets.
- Distinct `InternalChannel::VerifiedDirectMovement` has a bounded
  **128-datagram** queue, maximum 1200-byte packet, limited to four
  currently authorized endpoint slots per local five-person party.
- Public source-only APIs in `yt_direct_physical_api_v264.h` expose
  explicit install, send, receive and revoke operations. These APIs
  are NOT the original `P2PCoopSendTo` or SHAD path.
- An endpoint can be provisioned only from a non-null
  `VerifiedPeerIngressV262` session that passes the live, matching
  server-granted pair/epoch/map and authenticated-endpoint checks.
  Raw UDP packets cannot create the whitelist; future production
  client/server code must provide the **genuine** trusted grant.
- V266 revokes all peer endpoint permissions and queued packets on
  original server-link reconfigure and P2PTransport shutdown.
- `test_hybrid_direct_physical_gate_v264.cpp` covers no-grant denial,
  unexpected IP/port, expiry, wrong SHAD magic/version, length caps,
  four-peer capacity, same-peer refresh, explicit revocation.

## Limitations and next genuine blockers

1. Real YT/shadNet server must mint and authenticate exact pair/party/
   instance/map/epoch grants and distribute pinned responder keys.
   **A caller-provided bool or manually built V262 structure is not
   proof of server authorization.** Do not enable it without wiring
   a genuinely authenticated LinkAuth/server grant handler.
2. Two-message Noise NK V260 currently exists as source components.
   It still needs to be transported over authenticated server
   signaling (tiny Hello/Answer relay works) and backed by OS CSPRNG.
3. Each client needs authenticated NAT probe/hole-punch, peer endpoint
   verification and rebind. Socket transport alone is not NAT traversal.
4. The V256 game client still passes `nullptr` as trusted route.
   The real peer send/receive loop must be wired to the V264 socket
   API and V262 original GameLinkPeer ingress under correct lifetimes.
5. Two to five real-client playtests, latency/CPU/egress measures,
   map warp, death/DBNO, invasions, disconnects and firewall cases
   must precede safe rollout.
6. Public CI checks original source anchors and the isolated C++20
   gate; a full modified YT/BBHost/shadPS4 Windows executable build
   is NOT demonstrated by these checks.

A separate `pull_request` trigger was added to both PR #85 and the
independent native PR #84 CI workflows, because the previous GitHub
connector workflow-run action only exposed PR-triggered runs and
returned no results for push-only workflows. Do not interpret empty
run lists as either a PASS or FAIL.
