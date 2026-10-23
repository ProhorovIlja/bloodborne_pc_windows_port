# Seamless Hunt V6: actual UDP prototype and peer RTT-aware Quick Play (2026-10-23)

## Verified local development artifact

Downloadable conversation artifact: SH-YT-DIRECT-P2P-PING-V6-DEVELOPER-20261023.zip

Validated locally: **46 Python unittest tests** plus **6 C++ CTest executables** all pass. Real UDP smoke `smoke_direct_udp.py` reports an authenticated game-data datagram delivered peer-to-peer over 127.0.0.1, then a simulated NAT endpoint change causes the data-plane to revert to relay without dropping the test packet. A corrupt packet and a duplicate packet are rejected. No external P2P, actual Bloodborne gameplay or Windows binaries have been verified.

Core Python files in downloadable development artifact:
- `p2p_transport.py`: real socket PROBE/ACK/PING/PONG/DATA, room+sender+recipient-bound HMAC-SHA256, anti-replay, separate direct/relay RTT stats, watchdog fallback, loopback-only relay mock.
- `ping_filter.py`: 3-sample median RTT from the actual peer (never VPS latency), direct verified vs relay, signed/authorized measurement requirement, stale ping expiry 15 seconds, strict 10-500ms cap.
- `ping_quickplay.py`: shares DBNO/scaling/invasion/region/build/occupancy filtering with browser, then evaluates authorized local peer RTT for each candidate before atomically reserving a slot. Re-tries next eligible room after full response. Category presets any/35/60/100/150/250ms.
- `smoke_direct_udp.py`: one-computer offline demonstration using real UDP sockets and simulated NAT rebinding.

**The test transport is Python and is not inside the Bloodborne runtime.** It requires out-of-band pairwise authentication keys and authenticated candidate endpoint discovery, absent in the current shadNet protocol. The relay mock is loopback-only by design and must never be publicly deployed.

Native C++ files **in the GitHub branch**:
- `tools/poc/yharnam/ingame-online/ping_policy.hpp`: same filter behavior and direct/relay distinction for future in-game UI.
- `tools/poc/yharnam/ingame-online/test_ping_policy.cpp`: native median RTT, stale/unverified/unauthorized samples and thresholds; now included in CMake offline CI.

## Integration prerequisites for an actual Windows game release

1. Server-signed, short-lived, room-scoped peer candidates obtained from observed UDP endpoints, with privacy choice before disclosing IPs; keys must come from authorized membership on shadNet, not client-supplied addresses.
2. Implement packet framing, HMAC/anti-replay, direct handshake, and route switching inside the game's existing native `emulator/src/core/libraries/network/p2p_sockets.cpp`; use the SAME P2P socket for NAT punch and game packets. Preserve source-virtual identity and SHLK vport framing.
3. Change `server/src/server_link.cpp` and `link_server.cpp` to authorize direct peers and cease forwarding only after verified data-plane negotiation. **Important:** `ServerLink::Hub::Routed` and `BloodborneWorld::RoutesPacket` currently gate game channel subscriptions. A naïve direct data bypass breaks this interest filtering and security; P2P must preserve equivalent authorization.
4. Continue Coop/RPC/world authority over Fornex and make relay fallback automatic on loss, symmetric NAT or CGNAT; deduplicate packets across route epochs to avoid duplicate game events.
5. Implement signed remote ping measurement request and UI controls in the game's existing `bbport/gpu/shim/bbport_overlay.cpp`, not in desktop launcher. Strict ping filters reject unmeasured or stale candidates; for a full party use worst RTT among remote peers if requested.
6. Merge V3 UI scale and V5 DBNO rule (protocol 8) and V4 group policy with native Windows and Linux server, including game runtime 5th-slot+invasion changes and regression tests. No claim that these have been integrated.
7. Build a downloadable native Windows client installer from pinned source, defaulting to Seamless Hunt's endpoint automatically (existing Fornex PoC: 199.195.193.131). Verify two real Windows clients, join/death/travel/invade, security, NAT, CPU and 200-client load before public release.

GitHub's currently visible native Windows successful build (2026-10-22 on feature/seamless-hunt) is an **older development artifact**. It DOES NOT contain V6 direct-peer feature. The branch feature/yharnam-dedicated-server-poc has not produced a new public Windows build via Actions at this point.

Nothing was deployed to the production CLS or the running Yharnam test server on Fornex, and no VPN is required for the intended architecture.
