# V80: session-unique application wrapping key over verified local mTLS 1.3

**Status:** development-only, localhost-only, source-integrated into the existing SINGLE Qt shadNet daemon. Explicitly disabled by default. **Not a public P2P server, not a real V75 offer issuer, not NAT traversal, and not a working Direct P2P game connection.**

## Why a new key path?

V78 established a real Qt/OpenSSL TLS 1.3 connection that rejects untrusted client certificates. V79 mapped a server-operator-pinned certificate DER SHA-256 fingerprint to an existing *signed-in* Yharnam Together game account and checked that account's current gameplay world epoch. Qt 6.4's public API lacks the modern TLS exporter needed to derive the V75 `SHG1` AEAD wrapping key in a portable way.

V80 uses a separate **per-connection, server-generated application secret**, delivered *only inside that same peer-authenticated TLS 1.3 connection*. This is a valid alternative to a TLS exporter when the TLS server's identity and TLS client's exact pinned game identity are already trusted. Never send the key through plaintext SHLK, HTTP or process logs.

## Actual native Qt behavior

`P2PTlsListener` has two additional fixed protocol operations:
- `YT-P2P/V80 BEGIN\n`: before responding, it again resolves the TLS peer's actual X.509 DER fingerprint against the local operator pin and authoritative live game account/epoch. It generates a fresh 32-byte secret with Qt's OS-backed `QRandomGenerator::system()` and responds `YT-P2P/V80 KEY <64 lowercase hex bytes>\n` **on the encrypted TLS socket only**. A second BEGIN on the same connection fails closed.
- `YT-P2P/V80 CHECK\n`: checks the *same* pinned certificate and *same* game account+epoch against the live shadNet world again. If unchanged, it responds with **only** `YT-P2P/V80 BOUND NO_GRANTS\n` and closes. If gameplay membership/consent/link generation changed meanwhile, it aborts with NO success response and erases the session secret.

Each `QSslSocket` owns a separate `P2PTlsKeySession`. It expires after V78's 5-second socket lifetime. `Clear` destroys the in-memory key on disconnect/revocation/normal closure. Existing connection cap, input size limit, mTLS verification, strict TLS 1.3 and loopback bind remain enforced. A replayed request cannot mint a second wrapping key on an already bound session.

**The key is not currently used to seal any V75 grant or stored across connections**, so it is not a functioning grant-delivery protocol. The plaintext inside the application layer appears as hex, but the bytes are encrypted by TLS on the wire. Treat the random key as sensitive; never log/test-dump the value. The key is *application-level*, **not** a TLS-exporter value, and cannot be assumed automatically unique across process memory snapshots or restored VMs without sufficient OS entropy.

## Verification

Real Qt/OpenSSL `test_tls_local_key_session.cpp` runs THREE independent handshakes using CI-generated throwaway server CA, server certificate, client certificate:
1. Same pinned/current game session succeeds, receives a nonzero 256-bit per-TLS-session key and checks it remains valid on CHECK.
2. A second independent connection receives a DIFFERENT key; the game's server-owned epoch changes before CHECK, which must deny without replying.
3. A third connection receives its initial key and then tries to issue BEGIN again, which must be rejected.

The existing V78 missing client certificate test and V79 initial BIND/revocation tests still run. `.github/workflows/shyt-v78-mtls-local-control.yml` composes the full pinned original game+server source and syntax compiles the original Qt server chain.

## Next steps before real Direct

- A real authenticated and encrypted application offer request protocol, server-side V76-V77 peer-scope recheck, both-player consent, protected V75 `SHG1` AEAD issue with a session-wrapping key only while its account/game epoch remains current, and proper one-time key rotation/zeroization. Must never accept client-generated candidate grants or world flags.
- Secure TLS identities and certificate enrollment/pinning on native Windows clients, plus a provisioned public access path. Local dev env vars and loopback cannot be exposed as production controls.
- Actual per-peer directional UDP keys, scoped revocation, NAT candidates/consent and direct-shared game socket `Arm` plus signed three-probe confirmation. Relay remains mandatory when inaccessible/untrusted.
- Game packet contents encryption: HMAC-SHP1 authenticates but does not encrypt the game data. Reliable GameLink ACK/sequence retransmit migration also remains unimplemented.
- Two physical PCs/gameplay testing, full Windows native binary packaging and 200-player server egress/CPU measurements.

**Do not deploy this development branch over working CLS Friends on Fornex.** No ports, account SQLite, service units, live server state or main branch were changed.
