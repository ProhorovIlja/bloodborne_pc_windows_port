# V71 native game SendFrame: Direct-first dispatch, fail-closed

**Status: code integrated into composed pinned Yharnam Together game source; Direct runtime still DISABLED.** No source branch or GitHub Action result from this change constitutes an installed playable Windows client or active P2P connection.

## Where the code runs

`patch_native_direct_tx.py` patches the **original** `emulator/src/core/libraries/network/p2p_sockets.cpp` in `compose_sources.py::run()` *after* V69 relay-traffic metrics and V70 actual inbound SHP1 HMAC demux.

At the original `P2PTransport::SendFrame()`, the game has already constructed the native 4-byte virtual-port header and SHAD gameplay payload and determined `Link::RoutesThroughServer` would route this peer via shadNet. **Before** `Link::EncodeData`, an empty `NativeDirectSender` is consulted.

- No server-established Direct pair (the **current state**): returns `RelayRequired` immediately; exact original `Link::EncodeData`, server addr/port, `Transmit`, metrics and game return value remain unchanged.
- Future trusted, server-approved and NAT-ready pair: callback must verify reverse `NativeDirectReceiver` link has the **same authenticated session pair and generation** and is `Path::Direct` after **three successful signed probes**. It also refreshes world authority and validates the **entire** native game frame under the existing `EligibleNativeWireFrame` policy, reliable stream ownership and payload MTU.
- A verified full-frame Direct send is submitted using the **existing game's physical UDP socket** by a trusted future cryptographic SHP1 encoder callback. No duplicate relay copy is sent.
- Missing authorization/reverse readiness, forbidden server-owned channels, map/owner invalidation, expired tickets, oversized SHAD or failed direct send fall back to the **original unmodified frame** via shadNet. Failed direct send enters a 10-second retry cooldown; continued reverse liveness must be reverified.
- `Stop()` and server link/account reconfiguration revoke both inbound and outbound candidate slots. In-source `TrustedReverseDirectReady` queries V70's MAC-authenticated receive state under the receive mutex, but is not wired to any grant installer today.

The native Direct sender/receiver support at most eight **server-approved peers in the current game group**. No global P2P mesh of all players on Fornex.

## Test guarantees and boundaries

`test_native_direct_tx.cpp` tests direct-first selection with an actual directional HMAC encoder/verifier and original synthetic native SHAD whole frames. A real `DirectIngress` receives three MAC-authenticated probes before the *send* route can turn Direct. Fail-closed cases include untrusted grant flags, mismatched pair, no current reverse probes, invalid destination, unauthorized channels (0x2F remains server-only), a fake inner sender, stale map/world state, oversized frame, send failure/cooldown and expired grant. Windows MSVC CNG + Ubuntu GCC OpenSSL tests compile independently; complete source composition tests confirm it physically patches the original `SendFrame` in the right position before server routing.

**NOT tested by these gates:** full native C++ game compilation/linking; actual online game session; server-issued encrypted grants and keys; real NAT traversal; 200-player load; gameplay latency/performance; Windows renderer/game packaging; safe reliable ACK/sequence migration. No game secrets or IPs are stored in GitHub. `SHYT_ROUTE_METRICS=1` V69 remains opt-in.

## Remaining release prerequisites

1. Authoritative account + room/role/epoch consent in live shadNet, with secure authenticated **encrypted** control transport for keys and candidate addresses (not plaintext legacy SHLK Hello).
2. Per-direction fresh keys with anti-replay and expiry; matching both inbound/outbound tickets; actual installer for `NativeDirectReceiver::Arm` and `NativeDirectSender::Arm` under the respective game socket mutexes, plus revocation and rekeying.
3. NAT candidate exchange and hole punching over the **same game UDP socket**; block direct until signed probes establish reciprocal path; relay for CGNAT and privacy-only users.
4. Proper GameLink reliability migration (sequence, ACK, retries, deduplication, route epochs), 2 separate PCs and long-game tests.
5. CPU, packets/s, bandwidth and frametime measurements at 2, 5, 20, 200 simultaneous players, contrasting current shadNet-only baseline vs verified Direct and fallback rates. No unverified claim of VPS load reduction.

Official live CLS server on Fornex stays unchanged, as do existing account databases and the Yharnam Together-only target.
