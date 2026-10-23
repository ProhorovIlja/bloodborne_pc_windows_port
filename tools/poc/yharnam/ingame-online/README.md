# Seamless Hunt: in-game multiplayer (native C++ policy prototype, 2026-10-23)

Target UX: Bloodborne -> System -> Co-op Team -> Hunt Online. The existing controller-friendly Team::Screen in pinned Yharnam Together bbport/gpu/shim/bbport_overlay.cpp already draws a full-screen team menu over the game and at character loading, with invites and world picker. Add multiplayer pages THERE, not in the separate launcher.

In-game options: Quick Play (single or group), public lobby browser, private room/invite/password, host PvP/invasion opt-in, scaling preset, level brackets, and Direct P2P / relay status and relay-only privacy mode. The native launcher still manages installation, game detection, graphics, mods and patches. It must preset Seamless Hunt servers (current PoC Fornex 199.195.193.131), no manual IP or VPN for players.

Group vs group invasion: keep defender parties and invader parties separate, match only hosts who permit invasion, reserve all attackers atomically, never split a premade group. Example 3 defenders plus 2 attackers occupies five TOTAL character slots. Must add hostile AI/targeting, player damage, invasions entry/exit and spawn, rewards and world progression isolation; a server-side room record is not an invasion mechanic.

Included: session_matchmaking.hpp is a portable C++20 policy core, test_session_matchmaking.cpp exercises multiple independent rooms, private/public, build and level filtering, distinct attacker/defender parties, invasion opt-in, atomic reserve/confirm, expiration, concurrency and gated 5-player count. CMakeLists.txt builds the test separately from production:
    cmake -S tools/poc/yharnam/ingame-online -B /tmp/sh-ingame-build
    cmake --build /tmp/sh-ingame-build
    ctest --test-dir /tmp/sh-ingame-build --output-on-failure

NOT YET IMPLEMENTED: linking these policies to the game's actual menu and real shadNet WebAPI/auth/database; the true fifth player slot, hostile damage mechanics or Direct P2P transport. Current Yharnam Together game supports 4 team members (TeamSize=4, guest signs 7/6/5, client lobby and HUD arrays size 4). Prototype rejects fifth unless separately marked runtime-certified for isolated tests; setting that flag does not make the fifth character playable.

Direct P2P: upstream shadNet presently forwards SHLK Data/game UDP via server/src/link_server.cpp (control-plane Coop/Rpc/world must remain central). Native game transport has existing UDP socket plumbing via emulator/src/core/libraries/network/p2p_sockets.cpp. Next real patch needs server-observed UDP endpoints and authenticated pair candidates, hole punching, verified bidirectional peer path, route epochs/dedup/order, channel and team filtering, safe failback to relay for CGNAT/symmetric NAT, client IP privacy opt-out. CPU/load improvements not claimed before actual two-player tests and 200+ client load simulations.

Privacy and safety: password checks must happen in server authority layer; a client cannot claim server_authorized_private=true. Test API should never be published to the internet with open registration. Do not modify production CLS or existing running Fornex Yharnam test instance in this phase. Discord Rich Presence (Blood Level + heuristic build from >=18 STR/SKL/BLT/ARC, party, location opt-in) is client-side and consent based; do not leak private room secrets or IP.
