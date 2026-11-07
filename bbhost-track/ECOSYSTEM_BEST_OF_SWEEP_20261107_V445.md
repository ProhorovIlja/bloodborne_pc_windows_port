# SHYT V445 — full-ecosystem best-of engineering intake (2026-11-07)

Scope: **one coherent BBSC: Yharnam Together product** with BBHost-based playable client, the Yharnam Together experience/launcher, secure low-load server and genuinely measured hybrid Direct P2P/relay. Native EBOOT-free Windows port and production Fornex/website are intentionally **out of scope** now.

This is a **bounded cross-project intake** and prioritized integration register, not a claim that the whole internet or every GitHub fork has been read, nor that unmerged code is safe. We inspected latest public releases, repository branches, PR states and selected fork parentage; we also reviewed existing private Google Drive source inventories and mod metadata without uploading proprietary game data. Every proposed integration requires exact source pin, license/provenance check, build and actual game/network validation before promotion.

## Sources and what to take from them

| Source (official unless marked) | Fresh evidence and actual value | Action / gate |
|---|---|---|
| droogie/bbhost | Stable v0.2.26 (2026-11-04); v0.2.24 currently pinned in PR #86; plugin API16 unchanged in v0.2.26; its HLE P2P socket code changed significantly with larger datagram chunking. Draft #218 is v0.2.28 frame pacing/stall diagnostics; #217 is API17 multiplayer signaling + Matching2 lifecycle. | **P0** opt-in v0.2.26 real plugin+STUN build V444; never blind-swap HLE P2P v0.2.24 patches or use draft #218 as a release. |
| CLSAMG22/BBSC | Actual Yharnam Together BBHost v1.4.0 published 2026-11-06; its source archive SHA256 is 7c00d46f01b67ff1cf12cef346c245960b627141a9c1047d00e2ceadd167ca04. Release expressly says BBHost edition has **not** been tested online. | **P0** real game-hook/NP entrypoint, BBHost launcher integration; V441 checked source archive and native hook loader, **not game playability**. |
| Amanises-Yharnam-Together/BBSC-Yharnam-Together | v1.4.0 five-player/team/invasion/HUD base; PR #539 Windows TLS truststore sign-in, #540 per-link flood drops without 15-minute shared-IP ban, #537 3D map game-folder update. | **P0** authoritative team and replay-safe routing. V443 tested original Qt #540 candidate, not deployed; audit other PRs separately. |
| ProhorovIlja/... PR #85 (own prior work) | Real source-pinned YT EdDSA signed pair grants V279, original Noise NK 4-way UDP V327/V330, encrypted original GameFrame V243. | **P0** reuse V442 (PASS with original YT v1.4.0); bind to **authenticated live server/world/endpoint** before Direct P2P, never recode already-tested crypto. |
| Supermedo/bloodborne_pc | Stable Windows 1.9.8.1 (2026-11-06), bundled five-hunter seamless mode and mod event-empty fix. PR #169 headless prepare/update, #163 native mod ABI + Hunter's Atlas 3.1, #168 offline Chalice glyphs, #166 GPU checkpoints/character recovery merged; branches perf-latency, beta-1.9.8, freeze-fixes. | **P0/P1** event-patcher edge cases, crash/rollback/update UX, mod compatibility. Do not mix its bb-probe ABI with BBHost without a bridge. |
| deadinside28/bloodborne_pc | Stable 0.7; PR #442 defers destruction of in-flight GPU sampler, PR #440 fixes command queue submission generation publication, PR #429 device-local host-visible guest memory. | **P0/P1** GPU use-after-free and queue race concepts, only after confirming equivalent BBHost ownership and Vulkan scheduler semantics. |
| Awakenchan/LanternEngine | Stable 0.9.38: long-session FPS decline, >60-FPS speed, FSR/DLSS smear, cutscene whitescreen and audio output fixes. Branch online-shadps4-0.20; open #94 high GTAO and #96 probe GI. | **P1** stability and frame-time fixes; HQ effects are **optional** and must not be enabled in low-latency baseline. Lantern Engine naming and additional GPL attribution terms require careful review. |
| vladtepes22/NightwatchCoop | Stable 0.2.7 (2026-11-04); direct party networking, opt-in invasions, VPN MTU handling, loss/rejoin behavior, boss aggro, Chalice, item idempotency, party cost telemetry, conditional async save. | **P0** gameplay sync and NAT/MTU regression cases. Its separate protocol cannot simply be plugged into YT GameLink. Preserve host rules / player authorization. |
| visy/bloodborne_pc_windows_port | v0.7.8; input pacing, real-time controller reads, Direct P2P parties, in-game map and item sharing; merged #16 fixes false 'port open' behind CGNAT; merged #26 scopes open LAN/VPN joins to local adapters. | **P0/P1** explicit network reachability honesty, input latency and save atomicity; strict firewall/auth & scene ownership checks before gameplay port. |
| Mrsuss60/bloodborne_pc_windows_port | Stable v0.9.0 (2026-11-07) shader-cache version migration without wipes, asynchronous pipeline cache saving under mutex, automatic NG+ safepoints, save manager, low-VRAM textures, Win32 crash fixes, UI stencil PR #190. | **P1** save/snapshot and cache migration strategies; do not copy bbport structures directly into BBHost. |
| Wozzardman/shadp2p | Original Bloodborne P2P signaling/shadPS4 fork; dev/bloodborne-seamless-co-op branch separate from main. | **P0** protocol provenance and client socket behavior, not as a replacement for YT's encrypted GameLink. |
| Wozzardman/shadnet-p2p | Original Matching2/summon server, dev/bloodborne-seamless-co-op; PR #6 signaling compatibility, #4 co-op disconnection, #1 seamless summon broker. | **P0** server identity, summon and P2P route compatibility, compare against YT release. |
| shadps4-emu/shadPS4 | Stable v0.21.0 (2026-10-30), active memory/graphics/input PRs; #5612 speculative spin-before-wait optimization (open). | **P1** only verified transferable renderer/HLE fixes; avoid busy-spin without power and p99 tail measurements. |
| shadps4-emu/shadNet | Stable 0.1.1; branches main, production, staging, and open #56 ID-auth tokens, #54 friend lists, #58 game-custom data, #59 communication restrictions. | **P1** server API and security ideas; YT shadNet has diverged, no automatic cherry-pick. |
| DarkIzuku/bloodborne_pc | public-performance-stability-v2 default; branches bbhost-enhancements-v1, offline-performance-precache-v1, launcher-redesign-v2, seamless-dev; release v0.4.1-stability.6. | **P1** mod switch isolation, atomic launcher config backups, keyboard labels, build-staging source. |
| AdrianCsT/bloodborne_pc | launcher/settings improvements and alternative upscaler branches feat/dlss-fg and feat/helixsr, develop and PR merge branches. | **P2** inspect UI and graphics options for parity, not presumed current baseline. |
| MaskZeus/bbbridge | A GPL-3 bridge between shadp2p/bbport P2P and BBHost P2P framing; source described in older BBSC research. | **P0 research** compare wire-level assumptions. A bridge is not automatically a secure crossplay service. |

### Verified derivative forks, not just originals

- LRF17/LanternEngine-NativePlusHDR -> Awakenchan/LanternEngine, branch lantern-Native+HDR. Nightwatch PR #10 adapts its HDR code. **P2 optional visual path**.
- LRF17/NightwatchCoop-NativePlusHDR -> vladtepes22/NightwatchCoop. **P2** compare GPU compositing and low-latency cost.
- smilinleader/NightwatchCoop-BBFSS -> vladtepes22/NightwatchCoop. **P2** source-diff before treating branch as a feature.
- YoucefNabil/bbhost -> droogie/bbhost, branch dlaa (DLAA native-resolution option). **P2** separate GPU/API/latency examination.
- HatsyRei/bloodborne_pc_windows_port -> Mrsuss60/bloodborne_pc_windows_port, contributed UI-mask fix PR #190. **P1** renderer bug case.
- DarkIzuku/shadp2p and oat018/shadp2p -> Wozzardman/shadp2p. **P2** inspect changes; do not assume forks contain superior networking.

GitHub name/fork searches also found many uninspected BBHost/Lantern/shadp2p derivatives. Branch names and claimed features alone are **not** proof; perform bounded parent divergence and source tests, favor substantive authored changes over empty forks.

## Google Drive: actual user-supplied assets and precedence

The gungrain@gmail.com Drive contains previous handoff notes, the BBHost 1.0.0 source tree, BBSC server research, both game data trees, and a MODS tree. Reviewed metadata includes MOAL, Jump on O+L3 / Jump Attack X+R1, multiple widescreen/UI variants, texture/model downscalers, FPS Boost, compact HUD, corpse removal, debug menu, font, SFX and appearance packs. Do **not** publish proprietary CUSA03173/Dark Souls III files or unlicensed mod assets. They remain private and are **not** needed for ordinary public CI.

A previous private mod source audit flagged conflicts:
- Performance Patch vs Enable Screen Space Reflections (1 contradictory patch byte).
- Performance Patch vs Uncap FPS++ (6 contradictory patch bytes).

These are XML/source findings, not a verified currently enabled selection. Our launcher should list exact mods, versions and file/patch collisions; support **per-user profiles**, reversible overrides, runtime rejection of corrupt patch stacks and explicit warning for conflicting gameplay event/param mods. Never silently auto-enable user mods in online sessions.

## Ultimate integration gates

1. **Real client first:** use CLS v1.4.0 BBHost YT game's **actual** hook/NP/NetSync path as integration basis. The standalone V400–V440 experimental plugin is useful for cryptographic and policy proofs but is not itself the shipping game client. Preserve legacy save integrity, exact region/build identity and consistent hooks.
2. **Modern baseline:** V444 source-locked 0.2.26 candidate, pinned commit bdc5cdf8be5f37188da9c2368e92be444fdc04cb, original API16 plugin, strict opt-in and CSPRNG STUN. Its HLE net.cpp differs from 0.2.25, so old V13/V19 telemetry patch **must be adapted and independently measured**, never forced onto changed source. Draft 0.2.28 is isolated.
3. **Direct P2P + relay fallback:** original game reliable/world/owner/map/invasion control stays authoritative; only eligible bounded and authenticated *unreliable* movement may offload when server-issued pair grant, cryptographic peer confirmation and transport reachability all pass. NAT discovery is not peer identity. On expiration, map/party/world change, loss or replay, revoke and fall back to server without duplicate Reliable/ACK.
4. **Server capacity and safety:** P2P-first when reachable, encrypted relay for strict NAT, per-team/recipient routing, no global fanout, QoS/ratelimits based on authenticated links, no ban of all users behind a shared IP due to a single participant. Include connection statistics aggregated without account tokens, IP dumps or game payloads. All changes staged until tested on the exact production config.
5. **Gameplay correctness:** five-member team; 5 coop, 4+1 or 3+2, possibly 2+3 if original rules support it (never promise unsupported composition). Death/DBNO HUD persists while still in party; party wipe, lamp/area transition, Chalice and boss transitions, invasion admission, duplicate loot and flags must be tested. Borrow Nightwatch/visy fixes by original *game event semantics*, not memcpy of engine offsets.
6. **Launcher:** single BBSC: Yharnam Together product; later TEST ribbon top-left. Unified graphics, performance, online/P2P/relay controls, mods, accessibility, patch conflict report, native-source provenance, signed atomic updates and rollback, dedicated save backups, privacy-friendly diagnostic export. Avoid launching two competing mod managers.
7. **Performance & proof:** collect same-scene CPU/GPU frametime p50/p95/p99, input-to-display, shader stalls, VRAM peak, CPU per BBHost process, NAT connect success, relay Mbps/pps and server CPU/memory at 2/3/4/5 clients. Disable expensive optional visual effects by default. Compare feature additions to the baseline; reject changes that regress stability or 1%-low FPS merely to increase maximum uncapped FPS.
8. **Release gate:** real Windows BBHost Bloodborne 1.09 playtests with two to five separate machines, closed/open NAT, high RTT and loss, reconnect/host leave/duel/invasion, session >1h, save restoration, crash recovery, signed installer/update. 5 synthetic Noise links ≠ five actual games. No live Fornex/site changes until candidate passes.

## Changes made in this sweep

- V444: upgraded **source-pin eligibility** (not production baseline) in bbhost-track/apply_bbhost_plugin_to_actual_host_v3.py for stable v0.2.26 exact API16/CMake.
- V444: upgraded OS CSPRNG STUN overlay source pins for v0.2.26 changed net.cpp while retaining explicit opt-in and fail-closed entropy; no guessed route telemetry replacement.
- V444: new GitHub Actions workflow yt-bbhost-v026-candidate-v444.yml builds the **real** source-only upstream host and YT-enabled plugin, plus OS STUN tests. Check CI status before claiming actual 0.2.26 full-host success.
- This V445 inventory records candidates across upstreams, forks, release notes, PRs, branches, website research and Drive. No claim of total internet coverage.


## 2026-11-07 extended external + private research: V447/V448

### V444 released BBHost 0.2.26: actual complete-host compile PASS

[Actions #42358003948](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/42358003948) built the real released BBHost 0.2.26 renderer and engine, our original YT protocol plugin, and proved OS STUN entropy failure is rejected. The candidate was staged on a disposable CI checkout. This is **not** CLS's complete game hook client, actual 5-game multiplayer, or a working public P2P route. The original 0.2.24 pilot remains pinned.

### V447: exact published CLS BBHost loader has an avoidable map-cache invalidation

Public `YharnamTogether-v1.4.0-bbhost-source.zip` pinned by SHA256 `7c00d46f01b67ff1cf12cef346c245960b627141a9c1047d00e2ceadd167ca04`; original `src/yt/yt_host.cpp` SHA256 `2223da0a3939fe0ba1218e47bfe3be1c0d585aa05558a6297f4077f80403a67e`.

Its `runtime_memory_generation()` increments **on every query** while original BBHost 0.2.24 and 0.2.26 already export `hle_kernel_maps_generation()` and `hle_kernel_snapshot_maps()`. Consequently the original YT `MemoryWindows` guest mapping cache is invalidated on every check, undermining the cache. More importantly, the original `runtime_memory_protection` maps *any readable* guest range to `Read|Write`, including actual read-only maps, and reports the current host stack as guest RW. The exact original `HasMemoryAccess` caches only guest ranges; so simply replacing the epoch without correcting stack classification would be unsafe.

**V447 introduced an opt-in candidate, default unchanged**, source-exact overlay of the real public CLS file, mapping snapshots with actual SCE CPU permission bits, no host-stack guest caching, epoch-snapshot race rejection and overflow/overlap tests. [Actions #42359482875](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/42359482875) PASS including AddressSanitizer and UBSan portable tests. Its new `BB_YT_FASTMEM_V447=1` path remains **EXPERIMENTAL, no in-game proof, not merged, not deployed**. Windows in-game crash/frametime/permission testing is the next gate before enabling it; test at 30/60/90/uncapped, loading/chalices/invasions, save and map transitions.

### V448: external standards and a lightweight ICE library candidate

Compared the original BBHost CSPRNG STUN and relay route to IETF [RFC 8445 ICE](https://www.rfc-editor.org/rfc/rfc8445) and [RFC 7675 consent freshness](https://www.rfc-editor.org/rfc/rfc7675). Consent is **per endpoint 5-tuple**, authenticated and periodically refreshed; new route/epoch requires new consent, and successful STUN mapping discovery alone never authenticates a gameplay peer. Our PR #85 already requires an authenticated recent direct probe (2.5 seconds) and signed grants; preserve this condition. Don't conflate STUN, ICE, game identity, and private shadNet control authority.

Additional source candidate [paullouisageneau/libjuice v1.7.4](https://github.com/paullouisageneau/libjuice/releases/tag/v1.7.4) exact commit `b89c792e3612faf2f12cf35bcc56857313a06be3`: small portable C ICE/STUN/TURN/consent implementation, one UDP component, IPv4/IPv6 and optional built-in TURN server. Its **MPL 2.0** source requires license/provenance review before any distribution. It is **only a NAT traversal candidate**, not a replacement for YT GameLink/Noise/EdDSA nor a reason to send all game packets to a TURN relay on the Fornex VPS. Explicit `NO_SERVER=ON`, `DISABLE_CONSENT_FRESHNESS=OFF` and static build. Real upstream source was successfully compiled in both **Ubuntu and Windows MSVC** in [Actions #42359852364](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/42359852364). No mixed NAT, CGNAT/IPv6, TURN budget, gameplay or tail-latency trials yet. Compare with existing BBHost STUN, not automatically adopt.

### Additional private Google Drive source metadata reviewed

The owner's account contains `CUSA03173`, the full Dark Souls III source-game materials, `CUSA03173-mods`, historical patch.xml/source compatibility reports and a `MODS` tree. In that tree, MOAL includes `script/talk`, the Jump O+L3 mod includes `action/script`, FPS Boost includes numerous `map` regions, and Compact HUD includes `menu/fe.gfx`. Those are high-risk **overlap categories** for seamless events, game behavior and the official YT HUD: never enable them together without file-path hashes, active patch XML overlap analysis, explicit host/client mod fingerprints, reversible profiles and a full game-save backup. The earlier source reports identify Performance Patch vs SSR and Performance Patch vs Uncap FPS++ contradictory bytes. **No mod payloads or proprietary game data are published or bundled into CI.**

### Current basis decision

The long-term product must **benchmark candidates**, not predeclare BBHost, Lantern, Nightwatch or BBPort universally best. BBHost 0.2.26 is the presently compiled source/runtime candidate. CLS YT 1.4.0 supplies actual game hooks, Nightwatch/visy supply mature *gameplay regression cases*, Supermedo/Lantern/deadinside/Mrsuss60/shadPS4 supply performance and stability ideas, and PR #85/BBHost/shadNet/libjuice offer complementary *network techniques*. An Ultimate build earns its name through objective, reproducible multi-client FPS/p99 CPU/bandwidth/save/NAT tests after legal, game ABI and server authority compatibility checks.

