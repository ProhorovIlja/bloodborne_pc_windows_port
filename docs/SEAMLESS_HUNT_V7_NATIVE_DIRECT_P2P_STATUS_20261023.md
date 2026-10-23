# Seamless Hunt V7 — native Direct P2P integration milestone (2026-10-23)

## Verified source artifact

Conversation artifact: **SH-YT-NATIVE-DIRECT-P2P-V7-20261023.zip** (93 KB, ZIP integrity checked; supplied to project owner). This is a **developer** source bundle, not a playable Windows release or VPS deployment.

Native C++20 implementation (OpenSSL::Crypto, portable packet/state core):
- `native_shlk_direct.hpp`: SHD7 frame encoding with HMAC-SHA256/16-byte tag, room+virtual peer address+session epoch+sequence binding; replay window 128 frames, explicit PROBE/ACK nonce handshake, PING/PONG, virtual-peer identity reconstruction, Direct -> Relay timeout and oversize frame relay fallback.
- `native_shlk_adapter.hpp`: mutex-protected native transport bridge keyed by virtual peer, accepts *only* pre-authorized candidates from an authenticated server, schedules probes, and handles real game frames. Candidate authorization is **not yet wired to shadNet**.
- `PATCH-BBPORT-NATIVE-DIRECT-V7.py`: fail-closed patch generator for pinned upstream `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, applying six anchored modifications to `emulator/src/core/libraries/network/p2p_sockets.cpp`. Does not alter original checkout. Keeps existing relay path when no direct peer is authorized.
- `test_native_direct.cpp`, `test_udp_loopback.cpp`, `test_native_adapter.cpp`, `test_patch.py`: compiled and locally tested.

### Verification evidence

- g++ 14.2 and OpenSSL 3.5: **3/3 CTest PASS**, including actual localhost UDP datagram delivery and a simulated relay endpoint after direct expiry.
- Python unittest **6/6 PASS** (exact source anchors, bad revisions, no double instrumentation).
- Read actual GitHub pinned `p2p_sockets.cpp`: **6/6 uniquely matching patch anchors**.
- GitHub Actions for the feature branch has **no confirmed successful run**. Native Windows `bb-probe.exe`, Qt shadNet with this feature, and online Bloodborne gameplay **not built or tested**.

## Missing critical integration for real-world users

**DO NOT SHIP OR DEPLOY V7**. Candidate authorization deliberately remains off. It is unsafe to disclose peers' real public IPs or pairwise secret over the existing unauthenticated/unencrypted SHLK exchange. `shadNet` must obtain both peers' authenticated consent, verify they share a game party, confidentially issue short-lived pair secrets/epochs and observed NAT addresses, then deliver candidates to the clients and enforce route expiry. The client must invoke NativeAdapter::Authorize *only after* authenticating this server control message.

**Critical gameplay correctness:** existing `ServerLink::Hub::Routed` and `BloodborneWorld::RoutesPacket` filter and authorize game channels *on the relay*. The same authorized channels must be enforced on Direct, otherwise bypassing the VPS also bypasses world and gameplay interest-management checks. Until equivalent authorization is in place, no real game frames go direct. On fallback, deduplicate cross-route packets and preserve arrival ordering expectations, inspect NAT rebinding and CGNAT cases. All Coop/World/RPC control remains server-backed.

The RTT filter in V6 must use peer-specific RTT for the host/all relevant party members, not the RTT to Fornex. The private/public lobby, DBNO, scaling, invasions and five-player runtime features are separate milestones and are not yet merged into one release.

## Runtime target and release UX

The final installer must default to the Seamless Hunt server address (current Fornex: 199.195.193.131), locate Bloodborne automatically, include the native Windows runtime and all validated game features, and require neither a VPN nor manual Git/Python/PowerShell from players.

The running Fornex test server (protocol 7) and production CLS infrastructure were **not modified** by this milestone. Avoid partial client/server version rollout: V5 DBNO introduces protocol 8 and needs a matched build.

**Next action:** implement authenticated peer-candidate messages on shadNet, receive and validate them in native BBPort, preserve channel restrictions, then compile/run a *matched* Windows client and Linux server in separate staging. Only after two real players and 200-user load tests should the one-click public release be published.
