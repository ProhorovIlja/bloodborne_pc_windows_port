# V244/V246: real two-message Noise NK peer handshake, YT v1.3.1 source

2026-11-01. Bloodborne Seamless Hunt, playable Draft PR #85.
This is a secure-key-establishment **component**, not production-enabled
Direct P2P or a server-approved multiplayer admission system.

## Source and design

Reuses actual Yharnam Together 1.3.1 pinned source:
- `server/coop/link_auth.h`: `LinkAuth::Noise::{Symmetric,Dh,PublicOf}`,
  ChaCha20-Poly1305, BLAKE2b, X25519, directional key split.
- `server/coop/link_crypto.cpp`: upstream Monocypher v4.0.3.
- `hybrid_peer_crypto_v241.h`: SHA-256 domain-separated binding of party,
  ordered hunter IDs, per-game instances, world epoch and map, as well as
  the direct peer encrypted GameFrame datagram session.

`hybrid_peer_noise_v244.h` performs the Noise NK **e,es / e,ee**
two-message pattern:
1. Hunter A receives Hunter B's static X25519 **public key via a trusted,
   authenticated game-server grant** for the exact active party pair.
   A chooses a fresh ephemeral private key from a trusted OS CSPRNG.
   Its first message contains an ephemeral public key and encrypted,
   scope-bound confirmation.
2. Hunter B validates the same party scope, decrypts the confirmation
   using B's server-approved static private key, creates a fresh
   ephemeral key, returns its public key and encrypted scope confirmation.
3. Both sides derive **different directional session keys** using original
   `Noise::Symmetric::Split()`. These keys can be passed to the original
   `LinkAuth::Session` via V241 for AEAD+replay-protected movement.
4. V246 fixes UDP response loss: an identical retransmitted *first*
   message receives precisely the cached ciphertext+keys; a changed
   first message cannot reinitialize the responder. The initiator's
   `Finish` also rejects a second derivation.

Synthetic self-contained test:
`test_hybrid_peer_noise_v244.cpp` checks byte-identical retransmission,
key agreement, encrypted GameFrame roundtrip, replay rejection, different
world/party, wrong static key, invalid version, shortened and tampered
handshake, and failed reply followed by correct reply. It uses synthetic
test secrets only and builds with the **real upstream Monocypher** in
`yt-playable-hybrid-policy.yml` on GitHub Actions.

## Security invariants not yet implemented

- The code does **NOT** authenticate the identity of B by itself.
  The caller must verify the responder public key was delivered over the
  authenticated game-server link with a server-approved grant and that
  the grant is current for exactly A/B and their game instances.
- Ephemeral private secrets must be generated from a cryptographically
  secure OS random source and kept out of logs, crashes, screenshots,
  telemetry, saved configs, and GitHub. The helper does not create RNG.
- The server must revoke stale grants, rotate keys after reconnect/world
  change, reject old or wrong-party handshakes and enforce hostility rules.
  Handshake replay and DoS limits require **transport-level** controls.
- UDP socket establishment, NAT/STUN punch, endpoint validation and
  rebinding are NOT implemented. Reusing YT shadNet client-server
  session keys is forbidden; use pair-exclusive independent peer keys.
- A passing synthetic test does not establish game wire compatibility,
  actual NAT reachability, relay CPU savings, or five-player correctness.

Keep the existing shadNet relay as default until the authenticated
server-grant/key flow and real socket transports have been end-to-end
validated and carefully benchmarked. No Fornex update performed.
