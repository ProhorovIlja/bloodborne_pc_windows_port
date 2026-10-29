# V92: SHN1 signed NAT probe on the ORIGINAL native Yharnam Together game UDP socket

**Scope:** source-only, behind `SHYT_ENABLE_TEST_LOCAL_MTLS` (the existing default-OFF developer build flag). The actual user-facing native client still routes all gameplay through the original shadNet server; this V92 change must never be described as fully functioning public Direct P2P.

## What is now linked into the game

The original pinned `emulator/src/core/libraries/network/p2p_sockets.cpp` class `P2PTransport` has ONE physical nonblocking UDP `host_socket` and ONE `ReceiveMain` thread. Incoming ordinary game datagrams are received via `::recvfrom(host_socket,...)`, checked against the existing `LinkCut` and `FirewallAllows` rules, and normally decoded by `Link::TakesDatagramFrom` and the virtual-port game `Deliver`.

The exact-source transformer `patch_native_same_socket_probe_v92.py`, applied only AFTER V86/V87 native full-ID game integration in `unified-v9/compose_sources.py`, adds a developer-only branch **immediately after original firewall checks and before Link::TakesDatagramFrom/Deliver**. Only datagrams with the explicit `SHN1` magic can enter this branch; every normal game/SHLK packet uses the unchanged original route.

The branch asks the **existing** V84 native sealed-grant inbox to revalidate a trusted server TLS grant for the current game/world and checks the original accepted `Welcome` + V87 link generation. It feeds the V91 full SHA256 account-pair/mutual HMAC/nonce/sequence/source-endpoint/expiry checks, and replies with V91 challenge responses through **the same original `Transmit` path and the same already-open `host_socket`**. It does not create a second UDP socket, daemon, socket port, relay or side protocol. Existing firewall, link-cut logic, and developer network-delay simulation continue to apply.

`TryPairedTlsReadyForNatTest` first obtains a **V91 coordinated paired SHG2 grant over the same authenticated native TLS session**, checks that the original game account was accepted by shadNet and the live V87 link generation did not change during TLS, and records its specific 64-bit pair binding. Legacy V85 *unilateral* grant requests clear this paired admission state, so they cannot be reused as NAT credentials. Only then can `TryStartSameSocketNatProbeForTest(initiator,now)` start a signed challenge with the exact current pair and link generation. These are **explicit trusted developer-only methods**, not game options, automatic launcher calls or public packets. It requires a current verified full-width SHG2 native inbox and an accepted current original server link. It can emit only an authenticated 144-byte `SHN1` challenge; responders receive on their existing socket. `SameSocketNatProbeVerifiedForTest()` exposes only a local diagnostic after the V91 handshake, not a game-routing permission.

Server/account reconfiguration and transport shutdown revoke the full-width pending grant and the entire V92 probe proof. New/changed game server link generations, rejected Welcome or quiet server invalidate subsequent proof processing even when the online ID string did not change. The SHN1 packet never enters gameplay decoding or mutation. Invalid signed control messages are consumed/dropped, never passed to the guest socket.

## Safety and remaining release gates

- Both original game peers must have the **same server-issued V90 pair binding/master** and valid V91 same-mTLS readiness proof, not independent V85 offers.
- V92 still does **not** send game data via Direct, arm V58/V60 encoders, migrate reliable ACK/sequence ownership or remove the original server relay. It never routes gameplay at all.
- Only *exact* original server-specified peer IP/port tuples are currently accepted. If NAT rewrites candidate endpoints or peers are under CGNAT/symmetric NAT, the handshake fails closed and all gameplay continues on relay. A production candidate discovery/refresh and retry policy is required.
- The original game's UDP socket still needs a real authenticated TLS V91 runtime caller, secure remotely managed client X.509 credentials, authorization tied to both current shadNet sessions and cert revocation, robust both-received-ready barrier, a measured two-real-PC Windows test and encrypted reliable GameLink transport before any Direct gameplay transition.
- Source-transformer tests are in `test_patch_native_same_socket_probe_v92.py`. Real two-socket V91 kernel-loopback crypto tests are separate. A real production game launch or actual same-socket peer NAT test has **not yet been run**.

Live Fornex, CLS Friends, firewall, database, player saves and `master` remain untouched. This branch stays DRAFT, isolated and unarmed.
