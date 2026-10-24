# Seamless Hunt V10: authenticated Direct game-frame channel guard (2026-10-23)

Purpose: fix a gameplay correctness and security gap before activating direct peer routes. V7 could forward an entire signed SHAD GameFrame directly, bypassing shadNet server/src/server_link.cpp routing and its per-channel policy.

Code in feature/yharnam-dedicated-server-poc:
- tools/poc/yharnam/direct-channel-v10/native_direct_filter.hpp implements a conservative C++20 Pass-only channel predicate from pinned Yharnam server/coop/packet_routes.h; rejects malformed, oversized, mixed or empty frames.
- tools/poc/yharnam/direct-channel-v10/guard_adapter.py changes archived V7 NativeAdapter outbound TryGame and inbound Receive; even HMAC-authenticated peer frames are rejected when they contain disallowed channels.
- tools/poc/yharnam/unified-v9/compose_sources.py installs the V10 guard into the consolidated Windows game source output after applying V7.
- tools/poc/yharnam/direct-channel-v10/stage_live_test.py stages the pinned V7 headers and instrumented adapter without changing existing sources; C++ tests check 68 channels, real mutual handshake, allowed and forbidden frames, timer failback.
- master .github/workflows/shyt-v9-source-gate.yml now validates V10 before composing and checks generated native adapter and header.

Tests (local Linux): 2/2 CTest (including authenticated P2P direct and HMAC-valid forbidden packet denial), 3/3 patch-source tests, 5/5 unified composer tests. This is NOT a compiled Windows Bloodborne runtime and is not deployed to the user's Linux VPS.

Critical remaining work: ServerLink has no authenticated peer-candidate/grant control plane; game NativeAdapter.Authorize is not yet reached by real player flow. Control-plane SHLK UDP is not encrypted, so real pair-key delivery needs secure ECDH, explicit mutual consent, route expiry, map/owner authorization and NAT/rebinding handling. Client net firewall may also block authenticated candidates.

Dynamic movement and player state (channel 0x06) stays server-relayed by the conservative Pass-only guard. Significant VPS CPU savings are NOT established. Server must authorize dynamic SameMap channels with short-lived revocable grants, preserving reliable framing before they can bypass server.

No production CLS service or Fornex server modified. Five-player runtime, in-game lobby browser/filtered peer ping, full DBNO game testing, real public installer and Windows/Qt server paired release remain pending.

Source: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/tree/feature/yharnam-dedicated-server-poc/tools/poc/yharnam/direct-channel-v10
CI: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v9-source-gate.yml