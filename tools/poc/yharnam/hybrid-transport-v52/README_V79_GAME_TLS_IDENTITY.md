# V79: local Qt TLS certificate pinned to LIVE game account/session

**Source-only, disabled-by-default, test-only local loopback control. Not yet a real public P2P authentication service, encrypted grant issuer, game client or deployed release.**

## Exact trust chain (not a client login field)

1. Original `shadNet` `LinkServer::SignIn` accepts account/secret using the server's existing game login protocol, and `BloodborneWorld::Service` holds the current authenticated game session.
2. A privileged test-server operator pins the **exact SHA-256 hash of the client certificate DER** to ONE existing online ID. No name, SAN, CN, client-submitted body field or username can create or change this mapping. A missing or duplicated pin is denied.
3. V78 has already finished mutual TLS 1.3 authentication with an explicitly trusted client CA, no fallback or ignored certificate errors.
4. For the exact single-line request `YT-P2P/V79 BIND\n` the V79 listener finds the verified peer *certificate* in the local pinset, then runs an unforgeable server-side callback:
   `ShadNetServer::CurrentDirectAccountEpoch(account) -> LinkServer::CurrentDirectAccountEpoch(account) -> BloodborneWorld::Service::CurrentDirectAccountEpoch(account)`.
5. The callback is **zero/deny** if the account is not currently signed in via game SHLK, if the online game session was forgotten, is duplicated, opted out (or is a legacy client), is loading/no map, is not in an active team/world, is cut out of the team, or lacks a server-generated V77 link generation. New Hello/map transition/restart/forget revalidate before each BIND; we do NOT cache a client-provided success Boolean.
6. Even on success, the only response is `YT-P2P/V79 SESSION_BOUND NO_GRANTS\n`. No session ID, account ID, IP address, peer data, key material, or P2P offer leaves the process. Each BIND is a one-off readiness response, not a persistent authorization capability.

## Composition and implementation

The real pinned Qt server source is modified in `patch_tls_account_binding.py`: `server/src/main.cpp`, `server/src/server.{h,cpp}`, `server/src/link_server.{h,cpp}`, `server/src/bloodborne_world.{h,cpp}`, and the original `server/tests/test_bloodborne_world.cpp`. Shared helper `sh_p2p_tls_identity.hpp` resolves the operator pin and enforces live state. The V78 `sh_p2p_tls_listener.hpp` consumes it after mTLS. Full source overlay is assembled by `unified-v9/compose_sources.py::run()` **after V78**, not a second server or a Python proxy.

No local TLS listener exists until the exact `SHYT_P2P_TLS_LOCAL_TEST=1` flag is set. The experimental operator can set both `SHYT_P2P_TLS_CLIENT_CERT_SHA256` (64 hex chars of the leaf DER SHA-256) and `SHYT_P2P_TLS_LINKED_ONLINE_ID` (the intended actual game online ID) in the trusted **local test process**; one without the other aborts startup. This is NOT public user registration or production enrollment. The endpoint remains strictly localhost (`127.0.0.1`), with V78 request length, connection count and handshake time limits.

## Tests

`test_tls_local_identity.cpp` runs an actual Qt/OpenSSL TLS 1.3 session with ephemeral CI certificates. It checks malformed pin rejection, mapping duplicate rejection, an authenticated certificate BIND success, then revokes the authoritative live-game callback and verifies a *new equally valid TLS session* cannot BIND again. The original V78 tests still verify missing certificate refusal and the old STATUS reply.

Original `server/tests/test_bloodborne_world.cpp` now asserts `CurrentDirectAccountEpoch` is nonzero for active opted-in accounts and zero after loading, explicit opt-out and disconnect. CI syntax-compiles `main.cpp`, `server.cpp`, `link_server.cpp`, `bloodborne_world.cpp` against Qt6 and generated protobuf, in the single complete source tree.

## Strict limitations

- A pinned cert is not yet a secure certificate **issuance or account enrollment system**, nor does it synchronize with the end-user launcher's identity settings. Loopback/test use only.
- `SHYT_P2P_TLS_LOCAL_TEST` must remain **disabled in production** until a separate security review, revocation/pin rotation, PKI lifecycle and rate-limit review.
- A working TLS channel does NOT automatically provide Qt 6.4's missing TLS exporter needed to feed a unique per-session V75 `SealedPeerOffers` key; **do not use static keys**, usernames, user passwords, or plain SHLK/HTTP to fill that gap.
- No online P2P IP or key exchange, no NAT candidate discovery, no native direct sender/receiver `Arm`, no direct throughput improvements, no gameplay encryption, no reliable ACK migration, and no playable native game package are claimed.
- Live Fornex CLS Friends server, account SQLite data, systemd units and firewall are not touched.
