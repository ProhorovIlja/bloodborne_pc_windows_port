# V93: no native game UDP receive-thread stalls while obtaining paired TLS

**Scope:** source-only developer validation inside original Yharnam Together native game `P2PTransport` and the existing Qt shadNet server. Shipping `SHYT_ENABLE_TEST_LOCAL_MTLS` remains OFF. GameLink gameplay never arms Direct in V93.

## Real performance/stability issue fixed

V92 correctly reuses the game's original `host_socket` for the 144-byte signed SHN1 NAT probe, but `TryPairedTlsReadyForNatTest` held `native_grant_mutex` while requesting V90 paired SHG2 and sending V91 READY on a potentially blocking TLS 1.3 connection. The original game's `ReceiveMain` uses that same mutex to validate incoming signed probes. A slow/reconnecting TLS server could stall SHN1 processing or cause latency spikes; this is not acceptable in a future playable client.

V93 updates `patch_native_same_socket_probe_v92.py` to allocate a **worker-local** `NativeSealedGrantInboxV84` and do the full pinned mTLS and READY HMAC exchange **without holding `native_grant_mutex`**. One atomic in-flight flag prevents overlapping developer TLS handshakes. Before beginning a new handshake, existing paired/native pending state is safely revoked under a short lock. After TLS completes, it checks the original game's current welcomed account and unchanged V87 link generation, checks the pending lease has not expired, and performs a short guarded transfer of the already-verified SHG2 result to the original game's own inbox. Crucially, the game `link_mutex` is **not** held when calling the identity refresh callback, avoiding a potential nested-lock deadlock.

`NativeSealedGrantInboxV84::TransferVerifiedTo` allows that short handoff without copying the wrapping key and without a new network roundtrip. It refuses self-transfer, invalid/revoked/expired grants and non-increasing TLS serial numbers; the worker copy of the pair master is securely erased. The original game inbox keeps its authoritative live world/consent refresh callback so later changes revoke the grant. All game SendFrame and original normal relay routing remain unchanged.

## Tests

- `test_inbox_handoff_v93.cpp` compiles on Windows CNG and Linux OpenSSL. It tests a real sealed SHG2 ciphertext, transfer, independent owner lifetime, serial replay rejection, consent revocation, world changes during handoff and expiry before handoff.
- `test_patch_native_same_socket_probe_v92.py` verifies the actual pinned original game's `ReceiveMain` uses the same host_socket, with SHN1 after firewall and before guest parsing, plus the presence of a worker-local TLS inbox and absence of a game grant mutex held across TLS network I/O.
- `.github/workflows/shyt-v93-nonblocking-tls-handoff.yml` runs both source-guard and crypto tests on Ubuntu and Windows. Do not report PASS until the jobs actually finish.

**Not done:** original native Windows game binary build with the **developer** compile flag enabled, two real Windows clients demonstrating actual original-game UDP hole-punching, public remote X.509 credential provisioning, server-confirmed final both-sided NAT barrier, signed NAT remapped candidate refresh, encrypted game datagrams, reliable GameLink ACK/sequence cutover or measurable server load reduction. V93 cannot yet establish playable Direct P2P. Fornex/production servers/master/account/save data not touched.
