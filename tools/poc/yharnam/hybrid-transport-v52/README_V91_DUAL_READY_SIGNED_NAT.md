# V91: independently proven dual TLS readiness and signed NAT challenge response

**Development-only, unarmed, no production gameplay change.** This is one original Yharnam Together native client and its single original Qt shadNet server. No new daemon, public TLS listener, gameplay proxy, CLS/supermedo interop, or alternative online protocol.

## Verified dependencies

V90 successfully exercised TWO distinct OpenSSL native game clients, each using its own pinned X.509 client certificate and TLS1.3 socket into ONE original Qt server, and each receiving the same authoritative short-lived SHG2 pair master. V89 proved independent A→B/B→A and probe/game HMAC keys cross-platform.

## V91: server-verified receipt from both players

- `sh_pair_key_schedule_v89.hpp` adds `ReadyProof=3` key-derivation purpose; the derived READY key differs cryptographically from all UDP probe and future game keys.
- `sh_pair_ready_v91.hpp` computes a 32-byte HMAC-SHA256 receipt over the recipient-specific SHG2 epoch, issuance and expiry, using a purpose-isolated directional key from the common V90 pair master. A small server gate precomputes **both distinct expected proofs**, stores NO raw pair master and refuses a wrong recipient/proof, expired pair, changed epoch/world, denied consent or replay. Its readiness state is **not** Direct authorization.
- `P2PPairLeaseV90` configures that readiness gate when the original server mints the mutual grant, revalidates both original game/LinkServer scope directions before each readiness receipt, allows A's READY to arrive before B asks for its grant, and erases the V90 server copy of the pair master immediately after B's grant has been delivered.
- `P2PTlsKeySession::PairedIssued` tracks that the **same certificate-pinned current TLS connection** actually received its V90 pair half. Only such a socket may submit `YT-P2P/V91 READY <64hex>\n`. Neither SHG1, V85 standalone SHG2, nor an unauthenticated/plaintext game/WebAPI packet may do so. The server returns `PENDING` after the first client and `BOTH_READY` after the second, without starting any Direct sockets.
- `NativeTlsLocalOfferClientV91` verifies the normal X.509 CA and server IP SAN, TLS1.3 mTLS, authentic current game identity/consent/world and the full SHG2 sealed grant, then sends its READY HMAC **on the same existing TLS connection**. It refuses malformed/non-authorized replies, zeroizes HMAC and leaves its game grant pending/unarmed.

## V91: actual OS UDP challenge response test, separate from game

`sh_nat_probe_v91.hpp` implements the **SHN1** 144-byte binary probe (128 bytes protected by a truncated 16-byte HMAC-SHA256 tag, purpose-separated via V89) with exact two full SHA256 account IDs, pair ID, world revision, monotonic sequence, sender nonce, echoed opposite nonce, and reserved-byte/length validation. A per-direction 64-packet replay window updates **only after MAC verification**. It accepts network source address and port from `recvfrom` only, and demands exact match against the trusted server-issued candidate. Missing/wrong endpoints, modified bytes, replay, wrong key/epoch/world and expired offers fail closed.

The separate `test_nat_probe_v91.cpp` uses TWO genuine OS UDP loopback sockets with 4-way Challenge → Response → Confirm → ReadyAck, verifies authentication/nonce echoes, tampering, endpoint spoofing, replay and expiry on Windows CNG and Linux OpenSSL. These are **test-owned sockets**, not Bloodborne's running original game UDP socket. The proof state never calls `Arm()`, touches a game frame, or bypasses relay.

**Important protocol boundary:** A successfully received ReadyAck at the initiator is not proof the remote side knows the last packet arrived. Both-sided NAT reachability plus actual server-to-both final ready barrier are required before gameplay traffic may switch. Current strict exact-endpoint policy intentionally fails closed under remapped/symmetric NAT/CGNAT; production candidate discovery and refresh will need signed original-game-socket mappings and robust relay fallback.

## CI and remaining blockers

- `shyt-v91-nat-probe.yml`: Windows native CNG and Ubuntu OpenSSL **real kernel UDP loopback** and dual READY proof tests.
- `shyt-v91-real-tls-ready.yml`: one true Qt listener, two separate pinned native TLS1.3 sessions and live READY receipts; server checks both account/world snapshots, rejects third replay.
- Original full Qt shadNet build, existing V90 two-client mTLS and unified pinned source provenance still compile as separate gates.

V91 headers are staged in the pinned native/source composition. They are **NOT** yet called by the actual original game UDP socket, no public certificate enrollment/rotation/revocation, remote authenticated TLS endpoint, signed NAT candidate updates, encrypted game frames, correct GameLink reliable ACK/sequence migration or measured two-PC Direct/200-player server offload. The V90 local server pair setup remains privileged in-process test-only. Live Fornex, CLS Friends, database, player saves, firewall and `master` remain untouched.
