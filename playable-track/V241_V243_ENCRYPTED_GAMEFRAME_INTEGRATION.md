# V241–V243: YT encrypted movement GameFrame end-to-end component

Date: 2026-11-01. Draft PR #85 playable branch.
Upstream source: official lKaniel/bloodborne-server v1.3.1,
`5d2305ee611ef1e03be39ff925f0da75c9a70393`.

## Actual implementation

- `hybrid_peer_crypto_v241.h`: original upstream YT
  `LinkAuth::Session` using vendored Monocypher v4.0.3 for
  ChaCha20-Poly1305, per-direction counter, tag and replay window.
  It authenticates a separate `SHDP` v1 datagram (NOT the upstream
  client/server `SHLK` header) carrying ONE original YT 1.3.1
  `GameFrame` of channel 6 unreliable player movement.
- Binds the encrypted payload to a domain-separated SHA-256 of
  party session ID, ordered IDs, instances, world epoch and map.
  The source sender, target instance and ACK=0 are revalidated before
  accepting plaintext. AEAD validation and replay detection happen
  BEFORE calling the original `DecodeGameFrame`.
- Separate directional **peer** keys must be established and
  authenticated by an external protocol. Existing shadNet
  client/server `LinkAuth` session keys MUST NOT be reused for peers.
  Invalid or equal key material/invalid party scope disables the helper.
  The code does NOT perform key exchange, NAT discovery or UDP I/O.
- `test_hybrid_peer_crypto_v241.cpp` exercises real Monocypher AEAD
  and YT GameFrame with deterministic synthetic keys. Verifies
  tampering, replay, wrong key/party/epoch, and invalid movement
  payload/ACK rejection.
- `test_hybrid_encrypted_roundtrip_v243.cpp` composes:
  `SendExistingGameFrameV240` -> encrypted wire ->
  `PeerCryptoDatagramsV241::OpenMovement` ->
  `AcceptAuthenticatedDirectMovement` ->
  original `GameLinkPeer::Receive`. A direct failure uses the exact
  same original receiver via unmodified server relay, while a late
  authenticated older movement frame is deduplicated. The reliable
  ACK travels to server on an ACK-only frame.
- Existing `yt-playable-hybrid-policy.yml` builds V240/V241/V243
  with pinned actual YT C++20 headers and original
  `server/coop/link_crypto.cpp` compiled from upstream Monocypher.

## Security/online release blockers (no shortcut)

1. Server-authenticated ordered pair **grant**: exact map, 5-member
   team, identity, instance, session, expiry, epoch and hostility rules.
   Must be revoked on leave, warp, hostility or reconnect.
2. Authenticated peer key exchange using reviewed Noise primitives,
   an independent derived key per direction/pair/world epoch and
   verified peer identity. UDP endpoint verification, rebinding and
   NAT/STUN hole punching. A local bool is NEVER proof of auth.
3. Wire these helpers into actual YT runtime, packet send choke point,
   socket/thread lifecycle, and same GameLinkPeer instance on ingress.
   No direct branch enabled by default until 1–2 are enforced.
4. A limited-rate server health/authoritative heartbeat and gameplay
   world consistency must continue even when movement goes P2P.
   Verify sequence wrap, key rotation, max-frame MTU, replay under
   loss/reordering, 2/5 independent clients and hostile invasions.
5. Measured CPU/bandwidth, p99 join/RTT and NAT reachability on
   real test hosts before production or any Fornex deploy.

## Nonclaims

Passing source tests does NOT mean direct P2P works in the game, that
the server no longer relays movement, or that BBHost and YT can join
one session. No real UDP sockets, live game, Fornex loadtest, or
retail Bloodborne data were involved. Do not merge Draft PR #85
or enable experimental transport without the blockers above.

## Upstream references

- `server/coop/link_auth.h`, `server/coop/link_crypto.cpp`
- `server/coop/game_link.h`, `server/coop/packet_routes.h`
- `emulator/src/core/libraries/network/net_link.h`
- https://github.com/lKaniel/bloodborne-server/releases/tag/v1.3.1
- https://github.com/droogie/bbhost/pull/196
