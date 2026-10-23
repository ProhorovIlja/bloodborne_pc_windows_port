# Seamless Hunt: in-game UI scale + hybrid P2P V3 (2026-10-23)

Verified pinned upstream: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`.

## What is in GitHub now

- `tools/poc/yharnam/ingame-online/PATCH-YHARNAM-TEAM-UI.py`: fail-closed, generates an isolated overlay source from pinned Yharnam `bbport/gpu/shim/bbport_overlay.cpp`. Inserts a controller/mouse operable ± UI Scale control in the existing full-screen **game** Team UI. Scales the member cards and their remove-button hit areas. No changes to the desktop launcher.
- `hud_layout.hpp`: scales one-row five-member card geometry to ~80% at 1920px, keeps lower font legibility limit for small screens; describes HOST/ALLY/INVADER roles. The full fifth gameplay slot and actual role feeds are **not yet connected**.
- `sh_yharnam_ui_scale.hpp`: stores 70–110% in 5% steps in `BB_USER_DIR/seamless-hunt-ui-scale.txt`.
- `p2p_route_policy.hpp`: per-peer Direct/Probing/Relay routing decisions, monotonically increasing route epochs and timeout fallback. **Only gameplay Data may become direct**. World/Coop/Rpc/Lobby always remain on Fornex.
- `test_p2p_ui_policy.cpp`, existing `test_session_matchmaking.cpp` and CMake CI.

**Validation:** seven exact source patch anchors were compared with the actual pinned upstream `bbport_overlay.cpp`, each uniquely present; offline local package V3 passed 3/3 C++ CTest and 4/4 patcher unit tests. The branch's offline CI workflow now also fetches the real pinned upstream source to test a generated overlay. No CI run confirmed yet.

## Other user requirements and guardrails

- UI and match options inside Bloodborne, not in launcher. Launcher just finds game/mods/saves and automatically points to Seamless Hunt Fornex; no VPN/manual IP required.
- Public Quick Play and browser, private sessions/verified passwords, host-controlled invasions/scaling; passwords always block random invasions, even when PvP is on.
- Defenders and invaders are separate parties. A downed invader can be revived by a standing teammate of **the same invading party**, not by defenders. When all invaders are down/gone, issue **return to own world**, not account disconnect or save wipe.
- The current runtime's team size and guest sign slots are four total, so five cannot be advertised as working. The 3 defenders + 2 invaders test represents rule-level capacity only.
- The current Yharnam server at Fornex still relays SHLK Data. `p2p_route_policy.hpp` does **NOT** send packets or lower CPU usage on its own. Real native game integration requires verifying server-signed room-scoped UDP candidates, mutual hole punching, channel authorization, replay defense, route epochs, dedup/order and failover; some CGNAT peers will still require relay.
- Production CLS services, databases, firewall and currently running isolated Yharnam server on VPS were not modified.

## Developer validation

```bash
cmake -S tools/poc/yharnam/ingame-online -B /tmp/sh-ingame-build -DBUILD_TESTING=ON
cmake --build /tmp/sh-ingame-build -j2
ctest --test-dir /tmp/sh-ingame-build --output-on-failure
python3 tools/poc/yharnam/ingame-online/PATCH-YHARNAM-TEAM-UI.py --source /path/to/pinned/bbport/gpu/shim/bbport_overlay.cpp --out /tmp/sh-patched/bbport_overlay.cpp
```

Source patch applies to the pinned upstream only and needs a full native Windows client build and in-game test before distribution.
