# V84: SHG2 offer authentication with full SHA-256 online IDs

**Development-only: V83 local-only TLS offers still use SHG1. Direct game traffic remains OFF.** No live Fornex access, public TLS listener, gameplay socket changes, or user identity migrations.

## Original production blocker

The original V75 SHG1 offer uses two 64-bit, truncated SHA-256 online identity tokens. Rejecting collisions **within one observed pair** does not cryptographically prevent other identities with matching prefixes. Before public Direct P2P, both peer identities must be bound with a full-width digest from **authenticated** Qt world state, and verified by the native recipient.

## New additive wire format

- `sh_secure_grant_v84.hpp` introduces a separate `SecurePeerOfferV84` + `SealedPeerOffersV84`. It does not modify existing V75 SHG1. Header `SHG2`, version 2, 12-byte fresh random nonce, 148-byte ciphertext, 16-byte AES-256-GCM tag: exactly 183 bytes.
- Both account IDs become **32-byte SHA-256** digests. Remaining epoch, pair, world, timestamps, game physical/virtual endpoints and one-direction MAC key remain bound inside AES-GCM ciphertext. Domain separation is `YT-P2P-GRANT-V84`. Nonce replay cache fails closed at 64 records/key; lifetime <= 30 s; expiry, peer, recipient, world and epoch must match.
- `sh_p2p_tls_offer_v84.hpp` computes the complete digest of `YT-P2P-V84-ID:` plus the original **server-confirmed** online_id. It refuses missing/invalid IDs and requires current authoritative `P2PLocalOfferScope`: exact authenticated TLS recipient, online epochs, world state and endpoints. It uses CSPRNG for pair and direction key, retaining the original V81 10-second local grant lease.
- Qt issuer test and portable tests require tamper, wrong peer/destination including identity differences outside first 64 bits, stale epoch/world, wrong key, expiry, repeated nonce and incompatible SHG1 record to fail.

## Important remaining gates

1. Wire new SHG2 into the **same** Qt server's actual V81 mTLS offer branch behind a version handshake. Keep older SHG1 disabled for public P2P, without breaking local V83 regression.
2. Add native TLS SHG2 recipient with actual 32-byte digest sourced from trusted native game account identity; fail closed on unsupported protocol or stale session.
3. Secure user certificate enrollment/revocation and remote TLS 1.3 endpoint. Prove server-side revocation and persistent replay denial across reconnects.
4. NAT candidate exchange/probes, encrypted gameplay datagrams, same-socket Direct send/receive Arming and reliable ACK migration, tested with **two PCs** and fallback under CGNAT.
5. Do not release or claim server-load reduction without measured game traffic. All traffic remains current shadNet relay.
