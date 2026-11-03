# BBHost as candidate runtime for Seamless Hunt: source-based migration gates
Date: 2026-11-03. **Experimental branch, not a playable release and not a true GitHub fork of droogie/bbhost.**

## The two missions remain independent

**Mission A, playable:** choose the strongest proven host for an installable single
Bloodborne launcher/client/server, targeting Yharnam Together's seamless rules,
five participants when implemented, hybrid authenticated UDP P2P and relay.
The working baseline/fallback remains [playable Draft PR #85](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/85):
original upstream YT 1.3.1 server and frozen Windows launcher compile and boot,
while patched original Windows BBPort game-client build is not yet green.
No existing game runtime code should be deleted on an unbenchmarked claim.

**Mission B, true native port:** [native Draft PR #84](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/84)
remains a separate C->COFF native engine/runtime path. **BBHost is NOT this
eboot-free task**: its executable loads the original decrypted 1.09 PS4 ELF
and provides PC versions of PS4 system APIs. The guest x64 game CPU runs
natively, but it still relies on that original executable.

## Evidence (2026-11-03)

* BBHost stable v0.2.24 = source commit
  `b0098e04b889e2e70b4af84be1ce809d7af3ff95`; public plugin
  `BB_PLUGIN_API_VERSION=16`; Windows/Linux; original 1.09 ELF loader;
  engine GX hooks, game settings and live plugins:
  https://github.com/droogie/bbhost/blob/master/README.md
  https://github.com/droogie/bbhost/blob/master/docs/rendering.md
  https://github.com/droogie/bbhost/blob/master/docs/plugins.md
* BBHost already implements private-server Matching2, UDP P2P, STUN,
  direct hole punching and relay fallback. This does **not** mean its
  protocol can directly exchange a YT shadNet session or signed world grant:
  https://github.com/droogie/bbhost/blob/master/docs/online.md
* BBHost PR #204 (v0.2.25) is OPEN; #141 reports 82-86 to 116 FPS
  in a particular CPU-bottlenecked setup, NOT BBHost-vs-BBPort on
  identical settings/hardware. No trustworthy cross-port multiplier
  measured: https://github.com/droogie/bbhost/pull/204
  https://github.com/droogie/bbhost/pull/141
* Yharnam Together v1.3.1 pins
  `5d2305ee611ef1e03be39ff925f0da75c9a70393` and currently
  builds its seamless rules from `emulator/src/core/bloodborne_*.cpp`
  inside BBPort, communicating with YT's shadNet + world/party server.
  `bbport/gpu/CMakeLists.txt` links these to its own `bbnet`. These
  are **not** source-compatible with BBHost's engine/plugin API:
  https://github.com/lKaniel/bloodborne-server
  https://bloodborne.seamlesscoop.dev/docs/architecture
* BBHost's documented *five players* refers to vanilla-style dual
  invaders in some late areas, NOT five seamless co-op teammates.
  YT upstream official v1.3.1 is four; YT #484/#486 are not merged.
  Neither is a proven five-person seamless session today.
* GPL: BBHost is GPL-3.0-or-later and the plugin API explicitly makes
  distributed native plugins GPL-compatible derivatives. Source imported
  from YT/BBSC must be checked **file by file** for its GPL-2.0-or-later
  or other licenses; binary-only or GPL-2.0-only pieces are NOT assumed
  legally mergeable. Keep license notices and source available.

## Hard compatibility blocker: owner's original game version

BBHost requires exact **decrypted ELF64** SHA-256:
`941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7`
for its *one* supported original 1.09 game executable. Its docs illustrate
CUSA00900. The owner's private Google Drive contains **CUSA03173**
(GOTY edition), and compatibility must be **verified**, not inferred from
matching `APP_VER 01.09`. Locally run:
```sh
python bbhost-track/check_owner_bbhost_109_v1.py --owner-private-eboot /PRIVATE/PATH/eboot.bin
```
Output contains only ELF64 and exact-match booleans: NO hash, game file
path, name, contents or size. No retail game files go into public GitHub CI.
If false: investigate the exact executable, correct update, and differing
region before writing any non-working BBHost co-op hooks.

## What to port and where (not blind merges)

| Layer | Candidate base | Integration needed |
|---|---|---|
| Game CPU loader, PC HLE, Vulkan, graphics, timing, input, saves | BBHost | Preserve proven native GX fast paths; benchmark first, assess active PR #204 before porting it |
| Seamless game logic: persistent party, state, doors, boss/flag sync, deaths, travel, HUD, invasions, DBNO | Yharnam Together/BBSC, review NightWatch | Replace shadPS4/BBPort-specific addresses and services with **versioned BBHost plugin hooks**, engine/param/event callbacks and safe state ownership |
| NAT, UDP direct reachability, relay, connection retries | BBHost networking as candidate | Adapt YT's authenticated team/session identities; no trust from bare STUN endpoint; signed grants, Noise/AEAD, epoch, consent, reachability + rollback; measure VPS bandwidth |
| Auth, party rooms, join policies, matches, character/team state, server persistence | Existing YT shadNet + coop world first | Build an explicit server bridge/protocol contract; don't accidentally join unrelated BBHost public-server accounts |
| Launcher, updater, mod loader, save/profile isolation, localization | BBHost shell + select proven Supermedo/YT UI | One launcher eventually; dual selectable engines until real BBHost YT compatibility and saves are proven |
| Graphics/QoL sources | shadPS4, BBPort, Supermedo, deadinside, Lantern Engine, forks/PRs | Selectively benchmark and port high-value compatible changes, preserve licenses, avoid duplicate render paths |
| DS3 and original Bloodborne owner files | Private local research for engine types/assets/ABI only | No private game content in repo or external server; native mission continues separately |

## Release gates, in order

1. **G0 executable:** owner's decrypted 1.09 image matches BBHost pinned hash; stock BBHost launches that owned image on target Windows PC, same settings as BBPort. Don't confuse a compiled plugin with this.
2. **G1 measurable base:** same PC/driver, game build, scene, resolution, visual quality and warm shader cache; disable frame generation for *real rendered FPS*; record median and p95/p99 frame times, 1% lows, CPU main-thread/GPU time, VRAM, stability in repeatable scenes. Accept only evidence of performance or stability advantage, not unverified ratios. This branch's frame-cadence probe is **NOT GPU-present FPS**.
3. **G2 seamless gameplay:** real original 1.09 game in BBHost, typed hooks mapped against vanilla YT actions, complete single-player boot/saves, UI/menu safe, no observable corruption.
4. **G3 real multiplayer:** YT-equivalent authenticated world/party server, two independent PCs join, move, attack, load/travel, die/revive, boss state/flags, disconnect/rejoin; both direct UDP and forced relay paths, NAT variety, timeouts, signed authority pin.
5. **G4 five-person launch:** up to five total players in the team's selected coop/invasion mixtures, no premature fifth seat, matchmaking filters, privacy/duels/invader permissions, no server unbounded relay load. Needs real five-client testing.
6. **G5 ship:** one stable signed/verified updater, launcher, BBHost client and server guide, rollback backup; gameplay regression, performance and server soak tests. No proprietary files in download. Keep old BBPort-based PR #85 as tested fallback until G5.

## Delivered by this experimental branch

- `shyt_bbhost_probe_v1.c`: actual GPL3-compatible BBHost plugin
  compiled using BBHost **official public header**, deny-by-default on
  unsupported 1.09, read-only frame callback and aggregate cadence
  reporting; **no game logic ported yet**.
- `test_shyt_bbhost_probe_v1.c`: actual Linux `dlopen` of built .so,
  mock BBHost public API smoke (including denied bad version and original
  binary mismatch), checks no writes/hooks.
- `check_owner_bbhost_109_v1.py`: local-only owner-game admission gate.
- `.github/workflows/yt-bbhost-pilot-plugin.yml`: pinned v0.2.24
  upstream checkout, Linux SO real dlopen smoke, Windows PE DLL cross
  compilation with matching exports and no private assets.

**NO assertion that CLS's latest private BBHost/YT prototype is publicly
available**. If a verified PR/branch/source from CLS emerges, review
it against these gates rather than claiming it has been integrated.
