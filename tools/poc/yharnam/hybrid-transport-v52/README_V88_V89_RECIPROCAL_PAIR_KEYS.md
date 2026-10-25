# V88–V89: mutually authorized Qt pair and native directional key schedule

Status: **development-only source and CI tests**, on the original Yharnam Together single shadNet Qt server and native client. Production relay stays unchanged.

## V88: two independently captured authoritative views

`sh_p2p_reciprocal_pair_v88.hpp` validates two reciprocal `P2PLocalOfferScope` snapshots: recipient A expects peer B and recipient B expects peer A; session generations cross-match, world revision is exactly identical, and both native/virtual endpoint tuples are complete. Same WAN IP with different source ports is supported. Disagreements, stale or missing online sessions, equal IDs, or missing/duplicated endpoints fail closed.

`patch_qt_reciprocal_pair_v88.py` adds **internal** `CaptureLocalReciprocalP2POffersV88` methods to the original `LinkServer` and `ShadNetServer`. They invoke existing source-side `CaptureLocalP2POffer` twice in opposing directions, check every field again after minting, and discard both secrets if server state changed. These synchronous reads are **not** an atomic lease across future asynchronous TLS connections: before using the offers, both game sessions/certificates/world must be re-checked again.

The two offers get one CSPRNG 64-bit `pair_binding`, the same 10-second validity and **the same fresh random 32-byte pair master**, protected separately by each recipient's own authenticated TLS 1.3 SHG2 wrapping key. V84's field is still named `direction_key` for wire compatibility. With V88 paired offers, it is a **pair secret**, NOT a key to install directly into Direct UDP.

## V89: independent direction and purpose separation

`sh_pair_key_schedule_v89.hpp` derives a local HMAC-SHA256 key from the common pair secret, ordered full SHA256 sender and receiver account digests, 64-bit pair binding and current server world revision, with the domain `YT-P2P-V89-PAIR-DIRECTION`.

A→B and B→A keys differ. Sender A's outgoing derived key equals receiver B's incoming derived key; likewise in reverse. NAT probe and future gameplay keys are separately derived. The raw shared pair secret MUST be erased upon expiry, reconnect, revoked consent, or failed session and MUST NEVER be used directly as a datagram MAC or AEAD key. The gameplay purpose key is **reserved**; authenticated but plaintext UDP is not acceptable for public Direct gameplay.

These derived keys are valid **only** for properly correlated V88 paired grants. The existing V85 one-sided TLS offer command still produces independently random secrets and must NOT be treated as a valid two-party V88 session. Both users' authenticated server-side session and accepted TLS grants still need a common-pair coordinator with revocation and denial of replays across reconnects.

## Verification and missing Direct gates

- [V88 Qt/OpenSSL two-way AEAD recipient test](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v88-reciprocal-pair.yml), source `test_reciprocal_pair_v88.cpp`
- [V89 Windows CNG and Linux OpenSSL directional derivation](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v89-native-pair-keys.yml), source `test_pair_key_schedule_v89.cpp`
- The preexisting original Qt server compile and unified pinned source gates still apply.

**Not shipped and not yet implemented:** pair caching between two separate mTLS clients, certificate enrollment/rotation/revocation, remote authenticated control, server-assisted NAT candidate discovery, same existing game UDP socket probe/response, encrypted Direct gameplay datagrams, atomic reliable GameLink ACK/sequence migration, fast relay fallback under CGNAT, real two-PC testing or measured server savings. No production Fornex/migrations/account/OS/firewall changes.
