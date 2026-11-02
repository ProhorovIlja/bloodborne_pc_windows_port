# V279–V283: genuine YT Monocypher signed server pair grants

Status: independent playable YT v1.3.1 Draft PR #85, 2026-11-02.

This is an **implementation of the cryptographic grant format, parser
and server membership eligibility component**, NOT a deployed issuer,
not the existing game's server authorization and NOT live Direct P2P.

## Source exactness

Original source commit `lKaniel/bloodborne-server`
`5d2305ee611ef1e03be39ff925f0da75c9a70393`.
Uses **its original Monocypher 4.0.3** EdDSA/BLAKE2b APIs
`LinkMonocypher::crypto_eddsa_key_pair/sign/check`, not an invented
signature or unsafe shared server/client HMAC secret.

`yt_signed_peer_grant_v279.h` includes:
- Server-only EdDSA signature across **canonical bounded binary form**
  (V282) with version, short ID lengths, signed sender/receiver pair,
  party/team, 32-bit instances and map, 64-bit world epoch, UNIX
  issued/expiry milliseconds (maximum 30s), both UDP endpoints,
  32-byte responder Noise X25519 public key and 16-byte OS-random
  single-use nonce.
- Client verification with a pinned authority **public** key and
  independent LIVE expected pair/map/instance/party/world epoch.
  A grant may be accepted within 5s of server issue for clock skew
  and expires before `expires_unix_ms`.
- V280 explicitly binds that same signature to the original YT
  `PeerCryptoScopeV241` and real responder Noise public key.
- V282 `EncodeWire/DecodeWire` serializes a complete signed grant
  with maximum 512 bytes, rejects malformed length/version/NUL fields,
  extra bytes and non-canonical forms. **Parsing never authorizes** a
  connection; EdDSA verification and server membership validation
  must still happen. A wire object from UDP is always untrusted.
- Synthetic tests exercising the ACTUAL pinned Monocypher functions,
  signature tampering, different world/instance/Noise key, expiry,
  wrong signature key, canonical wire format and malformed packets.

`yt_server_team_grant_issuer_v283.h` adds a **server-only** template
with exact generated bbcoop::Team accessor API
(`Team.id/party/started/members/member/state`). It refuses to sign
for non-playing/offline/title members, duplicates, unstarted teams,
untrusted sender identities, wrong party or unsupported team sizes.
The limit is passed from the authoritative server runtime. **Current
official 1.3.1: 4. A future full team-five integration: 5.**
Its test uses a small synthetic team with the exact protobuf accessor
names, not a real running shadNet TeamLobby.

## Remaining production-critical wiring (not accomplished)

1. Owner-run server must create a SEPARATE EdDSA signing seed from
   OS CSPRNG and protect its 64-byte secret. Never derive it from
   the existing server X25519 Noise key, client secret or test seed.
2. A new server signaling/protobuf delivery must send the **public
   verifier key** and issued pair grants ONLY within the existing
   authenticated original `LinkAuth::Session` server->client channel.
   Clients must not pin or replace that verifier from an arbitrary
   peer datagram. The server must read real current TeamLobby,
   authenticated Link session identity, world map/session instance
   and server-observed peer endpoints, NOT client-provided claims.
3. Verify the signature against the pinned authenticated authority,
   check current party/world epoch and sender/recipient, then bind the
   grant to exact `PeerNoiseV244` X25519 handshakes and V262
   authenticated physical receiver/endpoint. Do NOT pass mutable
   `VerifiedPeerIngressV262` booleans as authorization on their own.
4. Bind each grant's single-use nonce to its key exchange and replay
   cache, revoke on member/party/map/connection changes, renew before
   expiry without forcing a constant reconnect.
5. Establish authenticated NAT traversal (real STUN/hole punching),
   integrate V265 physical socket and V255/V262 game send+receive
   into the actual YT client. Do not alter shadNet's world, invasion,
   trade, or reliable-stream authority. Load test against Fornex.
6. Perform 2–5 computer tests, disconnect/rejoin and rollback. No
   production server credentials or proprietary game bytes in GitHub.

**The tests are source-level original crypto and synthetic membership
fixtures, not live server/client multiplayer.** No Fornex changes.
