# V260–V263: Noise wire fix, original YT game receive, physical UDP truth

Date: 2026-11-01. Playable Yharnam Together v1.3.1 Draft PR #85.
Pinned official upstream SHA 5d2305ee611ef1e03be39ff925f0da75c9a70393.
No game assets, no production keys, no live Fornex change.

## V260: critical Noise NK defect fixed

The previous V244 code initialized the decrypt buffer to the expected
**plaintext** party binding before `DecryptAndHash`. This is invalid:
Noise must authenticate and decrypt the **ciphertext bytes received on
the wire**. Both initiator Answer and responder Hello paths were wrong.

V260 now copies exactly `BindingBytes` encrypted bytes from offset
`Magic.size()+LinkAuth::KeyBytes` in each received datagram BEFORE
calling original `LinkAuth::Noise::Symmetric::DecryptAndHash`, then
compares the decrypted binding against the immutable party/pair/map/
epoch hash. It preserves the pending initiator state on invalid reply.

Synthetic-original-YT test `test_hybrid_peer_noise_v244.cpp` now asserts
both wire payloads are encrypted, and that ciphertext or tag tampering
is rejected. A formerly impossible valid Noise hello/answer roundtrip
is now source-correct (full CI execution not yet confirmed).

## V262/V263: actual game-client ingress and shared original receiver

`yt_game_link_direct_ingress_v262.h` handles a peer **movement-only**
datagram only after checking:
- Exact source IP and UDP port from server-approved verified endpoint.
- A real installed Noise-derived YT `LinkAuth::Session`.
- Exact live server-issued party, ordered peer, run instances, map and
  world epoch matching the *same* cryptographic session.
- Fresh bounded direct-route lease; only original channel 0x06.
- Original GameFrame sender identity, target instance, packet class,
  payload length and the YT AEAD tag/replay window.

Only afterward does it call the **original** `GameLinkPeer::Receive`
by reference. No second receiver exists, so relay and P2P share
sequence/dedup semantics. V263 upgrades the V255 end-to-end source
bridge test to use this true ingress guard, not a bare
`PeerCryptoDatagrams::OpenMovement` call. A separate V262 test covers
spoofed endpoint, revoked grant/epoch, tag tamper, replay and late
movement after original server relay.

## Physical network transport audit: the remaining blocking point

The original YT source **intentionally prevents direct peer UDP**:

- `emulator/src/core/libraries/network/p2p_sockets.cpp`:
  `P2PCoopSendTo` -> `P2PTransport::SendInternal` ->
  `SendFrame`. Its comments state frames go the server route.
- Its `ReceiveMain` calls `Link::TakesDatagramFrom` before delivery,
  dropping datagrams from peers that are not the configured server.
- `emulator/src/core/libraries/network/net_link.h`:
  `Link::SendsToPeer` means the server is configured, NOT that
  the physical packet bypasses the server.
- `emulator/src/core/bloodborne_patches.cpp`:
  `RunGamePacketLink` currently receives only those server-delivered
  SHAD GameFrames using `P2PGamePacketsRecvFrom`.

**Therefore, do NOT claim that V255/V262 currently enable direct P2P.**
The next physical-layer change must expose a *separately typed* SHDP
movement route through the existing OS UDP socket (prefer avoiding
extra physical ports), require the server grant + Noise + endpoint
binding before transmitting or accepting peer datagrams, and never
relax the ordinary server-only shadNet frame policy. Raw peer SHAD
frames and untrusted world/state channels must stay forbidden.

Still needed: authenticated grant distribution and revocation from
the actual YT server, CSPRNG, NAT discovery/STUN and hole punching,
direct UDP socket routing, peer entry/rebind/lifecycle integration,
production game-client build, multi-PC 2–5 hunter playtests and
Fornex CPU/egress benchmarks. Do not enable peer mode under only
boolean flags or guess a peer endpoint.
