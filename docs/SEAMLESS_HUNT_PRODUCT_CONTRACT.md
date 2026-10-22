# Seamless Hunt PC — Product Contract / single cumulative release

**Owner request captured:** 2026-10-22. **Canonical reference for future development chats.**

## 0. Non-negotiable outcome

Deliver **one** optimized, stable Windows-native Bloodborne PC client, **one** approachable launcher, **one** configurable gameplay/mod layer, and compatible online services. This is a cumulative integration project, **not** a series of user-facing experiments, installers, or stand-alone test builds. Preserve existing work rather than repeatedly regressing to an older branch. Do internal CI, offline, integration and hardware tests before asking the owner for a full acceptance test.

- Use the existing `ProhorovIlja/bloodborne_pc_windows_port` repo and `feature/seamless-hunt`; keep `master` and production Seamless Hunt untouched until a separately approved, validated release.
- Main architecture: native visy-derived Windows runtime + its existing party gameplay, **not** a required shadPS4 emulator alongside it. Legitimate user's Bloodborne 1.09 files remain external to the distributable.
- Existing production realm: `play.seamlesshunt.com`, shadNet, GameServer, registration website, control/P2P relays. Protect ordinary BBSC clients, matchmaking, credentials, saves and uptime.
- Prefer direct encrypted P2P with NAT/STUN/IPv6 and adaptive authenticated fallback only if direct negotiation fails. Optimize connection success, connection latency, frame-time stability, startup, VRAM and CPU usage, **without promising physically impossible zero network delay**.
- Native-to-native party and **legacy BBSC shadPS4/BBPort interoperability** are separate requirements. Official current CLS BBSC 0.0.2 is the reference baseline; archived test5 is for regression archaeology only. Existing BBSC users must not install this native client or any custom plugin for interoperability.
- Compatibility with actual PS4 consoles is a **distinct unverified platform target**, not a confirmed capability. Do not advertise it without proof, including platform identity/security constraints.
- Do not rename diagnostic-only `Check BBSC login` as gameplay sign-in or treat a ping, STUN response, server login, matchmaking claim, NP room join or UDP connection alone as a completed co-op session.

## 1. One-click launcher experience

The default screen must answer: **Who am I? Can I play? How do I launch? Who can I join?** Onboarding: select existing 1.09 game folder, choose character/profile, log in to Seamless Hunt, press Play. Detect missing dependencies, permissions, account/session conflicts, controller/GPU/driver compatibility, and server reachability with concise actionable messages.

Suggested information architecture (not seven pages of undifferentiated toggles):

1. **Home / Play:** game files, character/profile, online status, co-op status, Play, safe launch history, GPU quick status.
2. **Online / Friends:** website-based account creation link, secure username/password sign-in when supported by server gateway, log out/revoke, friends/invites, public/private sessions, region/latency, host/join, password, PvP/invasions, connection mode `Auto (Direct first)` / explicit Direct / allowed Relay, server selector, party code and bell compatibility.
3. **Graphics / Performance:** hardware-aware Recommended / Low latency / Quality presets; resolution and **numeric render scale** only if fully supported by runtime; FPS target, VSync, pacing, frames ahead, DLSS/FSR/XeSS where genuinely supported, frame generation, Reflex, HDR, VRAM streaming, shaders, display and input. Clearly show requirements and safe fallbacks.
4. **Game / QoL / Mods:** searchable and categorized switches for gameplay, revive/death, bosses, lamps, progression, rewards, events, co-op, item handling, spectator, accessibility, input and approved mods; conflict detection, per-mod provenance and clean disable.
5. **Profiles / Saves / Updates:** multiple character/configuration profiles, isolated party saves, backups/restore with preview and rollback, reproducible modpack, signed/hashed staged updates and release channels.
6. **Tools / Support:** one-click private redacted diagnostics, connection doctor, benchmark/auto-tune, crash repair, safe cache maintenance, last-session report, log/privacy preferences, website/Discord/docs/credits.

**UX requirement:** simple mode by default, clearly titled categories, good typography, brief inline explanations, search, advanced settings collapsed, sliders with units and value entry, sensible automatic defaults, visible reset, no duplicated competing settings across launcher and game. Advanced experts can inspect exact values and source/config keys. In-game options should sync with launcher via `bbport.ini`/supported game APIs, not compete as independent copies.

## 2. Online and security acceptance

A working account flow means verified login and **actual game session binding**, not a disposable TCP credential check. User can register/manage the account on `https://seamlesshunt.com` and sign in/out from the launcher with an intuitive username/password experience. Implement a **TLS-secured server-side gateway or an equivalently sound authenticated browser/device flow** before persisting credentials or sending sensitive tokens. Legacy shadNet login uses unencrypted TCP; **never silently send raw user passwords as if this were a secure native launcher login**. Use platform-protected credential storage and short-lived scoped/revocable tokens as applicable; never log passwords, tokens, party secrets or other players' private data.

Gameplay milestones must cover two directions against **unmodified official CLS BBSC clients**:
- Native host accepts shadPS4/BBPort clients; native guest joins shadPS4/BBPort host.
- Account identity, character selection, bell/summon discovery, room membership, NP/Matching2 equivalence, signaling, NAT traversal, game actor spawn, position/state replication, damage and world-event sync, map transfer, disconnect/rejoin, death/respawn, lamp recovery.
- No wildcard routing that bypasses user password, session ACL, modpack compatibility, game version or PvP restrictions. No mixing unrelated sessions; no sending arbitrary clients into rooms.
- Test every connection direction under direct/open NAT, symmetric NAT/CGNAT, firewall/IPv6, unstable networks, relay outages and slow links. Measure connect success percentage, p50/p95 time-to-join, RTT, jitter, packet loss, relay usage, bytes/sec and CPU overhead. Do not guess numbers.
- Preserve current visy encrypted party P2P, code and local/offline support. Version negotiation is mandatory; do not splice incompatible wire formats because both use the same hostname.
- Where the public CLS protocol does not expose information required for native session binding or identity, implement and test an explicit compatible adapter instead of inventing fields.

## 3. Gameplay and QoL scope

**Preserve existing visy 0.7.2 feature baseline** with real implementation audits and tests: seamless session, revive/respawn and death rules, shared/open-world flags, guest rewards, NPC/dialog/story options, boss and chalice behavior, lamp/area transitions, co-op HUD/pings, save safety, party restarts, mods, input and PC graphics.

**Evaluate and selectively port unique, compatible improvements** from these families. A mention is not proof that the source's implementation is already ported:

| Source | Candidate benefit | Integration constraint |
|---|---|---|
| visy, Mrsuss60, deadinside28 | Native CPU/Win32 runtime, party, saves, Vulkan base | Preserve newer baseline and existing working hooks |
| Awaken / LanternEngine / DarkIzuku | Frame pacing, VRAM management, input, drawing, shader/cache improvements | Reproduce exact baseline/patch chain; benchmark and regression test |
| Supermedo, 0xCydral, AwesomeObserver, FIocker | Auto benchmark/presets, GPU capability UI, upscalers, Reflex/FG, packaging | Test GPU/driver matrix; avoid duplicated or falsely labeled features |
| NightwatchCoop | Practical Awaken + visy integration examples, WPF navigation | Not a new multiplayer protocol; do not downgrade visy's newer party code |
| Yharnam Together | Downed/revive, shared world ideas, recovery and progression invariants | Central-server world model cannot be grafted into P2P directly |
| bbhost | Secure patch preflight, mod/plugin concepts, param overrides, NP/server lessons | Build compatible plugin API, do not load arbitrary bbhost DLLs |
| CLSAMG22/BBSC, shadPS4, shadNet, bbhost | Bells, legacy matchmaking/signaling, game actor sync, helper infrastructure | Versioned interoperability, preserve existing population |
| Nucleus, QoL/mod/Discord sources | Optional local multisession, achievements, Discord rich presence, camera/spectate, More Options at Lamp, accessibility | Respect licensing, conflicts, mod ordering and save integrity |

**Dedupe rule:** audit each candidate by actual code, version and license; if already present upstream, don't re-add it. Preserve copyright/credits and do not distribute retail game content. Features requiring incompatible architectural rewrites or unsupported hardware stay opt-in/experimental and must not secretly compromise base stability.

## 3a. Final gameplay extras and patch catalogue policy (2026-10-22)

**Priority order:** the native Windows executable, stable interoperable BBSC gameplay/account/online,
quality launcher/onboarding, GPU/performance and resource-efficient server come first. Optional
mod/cheat content never blocks the core release and is not counted as successful networking.

**One catalog, no competing hooks:** combine the community GoldHEN/shadPS4 XML patch
inventory, port-native gameplay/effect toggles and third-party optional cheats in one searchable
launcher UI, with explicit categories (core fixes, QoL, gameplay, accessibility, experimental,
offline cheats), provenance, licensed content, known compatible CUSA 1.09 hashes, conflicts,
startup-only vs live toggles, saved profiles and rollback. A patch is enabled only when its
original byte sites and dependencies are verified against the actual user game executable.
Exclude duplicate writes, incompatible FPS/hook/renderer edits, obsolete fixes superseded by
native code, and known crash/save/online hazards. External XML remains supported but NEVER
blindly promoted into the built-in always-on defaults.

**DollRebirth/MOAL:** expose the Doll respec *XML patch* in the optional patch catalogue
with default OFF, version/byte-site validation and a dependency check for the DollRebirth
talk assets. The lamp-service mod MOAL remains optional and solo-only until tested.
Our existing native direct-lamp travel and MOAL's lamp talk replacement cannot both own
the same script/menu. The current archive importer does not authorize bundling original
game/mod assets in public releases. Respec state changes need user confirmation, pre-use save
backup, and no unverified PvP or mixed-client network operations.

**Separate jump from run/dodge:** the native input remapper already exposes Circle and L3 as
different PS4 actions. An independently working Jump-on-L3 gameplay script should be offered
as an easy built-in input/gameplay preset with default compatibility checked, reversible switch,
and gamepad/keyboard rebinding. The uploaded Classic v2.1 modifies `c0000.hks` and must not
be merged simultaneously with any other mod rewriting that file. The Nexus mod's newer v2.8
also offers a Modern version and additional bug fixes; investigate source/license and
verify against the 1.09 original before adopting or redistributing anything. Never publish
Sony/From game files embedded in a full rewritten script unless redistribution rights permit
it; prefer legitimate source patches/deltas against the user's own copy.

**Optional manual New Game Plus after an ending:** research the two independent existing
solutions, Bloodborne Enhanced's `Prevent Auto New Game Plus` (speak to Doll to begin next
cycle) and Stake of Marika's explicit New Journey menu after an ending. The original game
automatically begins NG+ after the ending. Our upstream visy party code already has
*guest choice to accept an ending*, but this does not delay NG+ for the host.
Implement an explicit opt-in `Auto NG+ / Ask / Manual` preference only after game-event/flag
audit, avoiding an irreversible partially committed save. At every ending, prevent the
transition safely *after* the story/ending event and achievements, preserve all current
world state and key items until user confirmation, offer the Doll or another unambiguous
in-game UI to start the new cycle, preserve the chosen ending, and make NG-cycle advancement
exactly once per owned save. Cover Yharnam Sunrise, Honoring Wishes, Childhood's Beginning,
Gehrman/Moon Presence, DLC progress, save/load/restart, death/rejoin and any host/guest
decision separately. Do NOT ship untested save-state hooks just to display the option.

**Network safety:** cosmetic/local client settings need not match; gameplay scripts, XML
patches, cheats and NG-cycle transitions participate in the existing party compatibility
hash/version checks. Unsupported mods are solo-only; cheats altering stats or enemy/world
state never silently affect strangers/official CLS players, server matchmaking or saves.
Leave experimental features disabled if their interactions with unmodified BBSC are unknown.

## 4. Server contract and resource efficiency

Preserve `play.seamlesshunt.com` existing public shadNet/GameServer accounts, registration, matchmaking, room isolation, relays and ordinary players. Any server work needs protocol/capability versioning, backward compatibility, backups/rollback and staging. Optimize true measured CPU/RAM/disk/network bottlenecks: rate limits, connection cleanup, efficient lookups, native fast paths if measured, log rotation and safe caching. Avoid per-user maintenance commands or production restarts for client experiments. Never deploy a candidate shadNet source just because a file name resembles the production SHA.

## 5. Definition of “owner-ready build”

A **single downloadable Windows installer or portable archive**, not developer source patches. It contains launcher, native executable, all licensed runtime DLLs/configs, integrated mods, full defaults and help; it excludes copyrighted game files and private service secrets. It must cleanly run with the owner's own 1.09 installation and profile.

Mandatory **internal release gates** before inviting the owner to test:
1. Reproducible Windows native C++ engine build, package and launch-chain smoke test. CI must distinguish source tests from **full engine build**.
2. Static/runtime mod and patch compatibility checks, game version checks, backup/rollback, conflict detector and clean solo launch.
3. Launcher onboarding, site registration link, *real* securely authenticated gameplay account (not merely login check), complete settings persistence/launcher↔game sync, game launch, GPU compatibility and update recovery.
4. Native host↔guest gameplay verification and real BBSC shadPS4/BBPort host/guest interoperability verification, including in-world remote character and correct save/progression behavior, or explicitly mark this target **not complete and do not call the release ready**.
5. End-to-end test matrix: solo; online 2/3/4 players; PvE/PvP; passwords; boss/wipe/death/revive; maps/lamps; rejoin; mods; save integrity and offline recovery.
6. Performance A/B on representative hardware with p50/p95/p99 frametime, 1% lows, VRAM, RAM, CPU and startup time. Low-latency tuning must be measured; quality/performance presets must avoid unverified claims.
7. Security/privacy scans, network fault injection, clean installs, updates/rollback, no forced unrelated public-server behavior change, signed/hash-verified package manifest.
8. Final version/hash/release notes, user-friendly guide, internal evidence and a **single owner acceptance checklist**. Owner testing is an acceptance pass, not a substitute for engineering or a nightly request to test each patch.

**Internal iteration is allowed and necessary** in GitHub. It must not create a pile of owner-facing mini-release ZIPs. A limitation discovered late should remain an openly tracked blocker; no pretending the full feature set is complete.

## 5a. Pinned legacy-online upstream and future localization

- **Priority reuse target:** deadinside28/bloodborne_pc release 0.6 commit `8185b88d80573fa300595d5c54450183b4109935` includes `gpu/bbnet20` and `docs/BBSC.md`: shadPS4 v0.20 network, NP/Matching2/signaling, game hooks, summon paths and relay. This is a **native Linux module**, **not a Windows DLL**, and the author's 2026-10-16 account explicitly says a second-player BBSC session was untested on the new module. Never call it verified Windows crossplay.
- `tools/interop/stage_bbnet20.py` stages and fingerprints those **exact** upstream sources in CI, rejects dirty trees, unexpected commits and symlinks, retains license/provenance. Actual Windows-specific port and safe integration behind a disabled flag remain to be implemented and compiled. Keep original visy party multiplayer intact.
- Full launcher and custom BBSC item/mod text translation is deferred until **after feature freeze**. See [LOCALIZATION_AFTER_FEATURE_FREEZE.md](LOCALIZATION_AFTER_FEATURE_FREEZE.md): official European Bloodborne has 14 screen languages including Russian; upstream Linux bbport documents 21 possible game text languages across region resources. English launcher default, Russian first, region-aware game/mod translations and fallback only at the later localization phase.

## 6. Current grounded state (2026-10-22)

- `feature/seamless-hunt`, draft PR #1, native-client-checks CI succeeded; full native Windows C++ build and cross-client game interoperability **not yet confirmed**.
- Existing `launcher.py` (Python/Tk, ~5k lines) already exposes Display, Graphics, Performance & Shaders, Game, Input & Audio, Advanced / Debug and Party, plus game options and many party switches. This is a functional starting point but **not the finished navigational UX**.
- Existing visy native party transport is separate from legacy BBSC. STUN/Network Doctor and a short-lived unencrypted shadNet account check already exist. They are tools, **not a connected game account**.
- User-provided legacy shadPS4 and Fornex handoff archives, working October 21 reference logs, historical gameplay fixes and source inventories have been analyzed; current CLS 0.0.2 is the public compatibility baseline. The latest shadPS4 v21.2 source changes were not confirmed in all historical exe snapshots.
- Server Python GameServer and BBHost snapshot SHA match the user's VPS inventory, while exact current deployed shadNet source revision is not proven. Do not change live production as part of native source integration.

**Engineering next:** close CI full-engine build, build secure account/service integration, implement and test *actual* legacy gameplay protocol bridge, then unify launcher UX and selectively integrate measured engine, mod and QoL improvements. Move toward **one integrated release**, never claim “top everything” merely from feature flags, source files or offline unit tests.

**Source context:** `docs/SEAMLESS_HUNT_ECOSYSTEM_AUDIT_2026-10-22.md`, `docs/SEAMLESS_HUNT_STATUS.md`, `docs/SEAMLESS_HUNT_NETWORK_DOCTOR.md`, `docs/NIGHTWATCH_COOP_EVALUATION.md`; private uploaded archives and conversation histories are deliberately not copied into this public repository.
