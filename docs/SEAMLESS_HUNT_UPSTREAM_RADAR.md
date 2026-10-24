# Seamless Hunt PC — ecosystem feature radar (2026-10-22)

**Purpose:** reusable, source-backed research inventory for "best from every world", not an indiscriminate feature list. Each candidate must be compared with the *actual current fork code* before a port is considered. Distinguish **already in native base**, **implemented by other projects**, **candidate**, **tested in this fork**, and **release-ready**. Never claim a concept in a README is a finished integration.

## Ground truth in this fork
- Native client fork: \`ProhorovIlja/bloodborne_pc_windows_port\`, branch \`feature/seamless-hunt\`.
- \`launcher.py\` already has a background GitHub release notice with a six-hour cache through \`scripts/update_check.py\`, Ctrl+F setting search, native party UI, modes, graphics, co-op and mods. This was **not** a full updater.
- This branch now includes \`CHANGELOG.md\`, a read-only \`scripts/release_center.py\` with bounded, fork-only GitHub release history, a What's New / Updates window, offline notes, packaging and tests. There is **no auto-install**.
- Existing visy-style native party, crash recovery, in-game settings, mod loader and save segregation must not be rewritten or duplicated merely to add a feature.
- Seamless Hunt/CLS legacy bell crossplay, secure production sign-in and full source-compatible update installation are NOT certified.

## Where useful ideas already exist

| Project/source | Verified documented capabilities relevant here | Decision and risks |
| --- | --- | --- |
| [visy native Windows port](https://github.com/visy/bloodborne_pc_windows_port) | Existing party co-op, recoveries, in-game options, rollback-safe party saves, shader cache builder, controller prompts, output presets, direct summon. Current README references 0.7.3; a release page version may lag source version. | **Existing baseline; audit diffs, don't re-add.** Keep same-build compatibility checks. |
| [Supermedo native Windows port](https://github.com/Supermedo/bloodborne_pc) | Hardware-oriented Smooth/Balanced/Quiet goals, save discovery/import with backups, setup troubleshooting, automated scene benchmark, localized UI, achievements, online options, mod patches, one-click updater preserving user content, text vs voice languages, Add to Steam. | **High-value candidate:** profile-centered onboarding, hardware presets and test harness; audit update code, save formats, license and hidden installer side effects first. |
| [Awaken/LanternEngine](https://github.com/Awakenchan/LanternEngine) | Native game execution with a dedicated launcher, renderer, Vulkan frame/VRAM optimizations, DLSS/FSR, updates, help site. | **Compare carefully** for proven frame pacing, cache handling and launcher UX; do not replace our runtime or adopt incompatible P2P blindly. |
| [bbhost](https://github.com/droogie/bbhost) | Native shader pipeline work, plugin/mod loader, parameter overrides, source-mapped patches, replay-like draw capture comparisons, diagnostics and performance tests; 0.2.18 release includes signed plugin assets. | **High-value internal technologies:** per-effect benchmark, signed plugin trust model and mod conflict checks. Validate Windows integration, licensing, ABI and rendering baselines. |
| [BBLauncher](https://github.com/rainmakerv3/BB_Launcher) and [Nexus entry](https://www.nexusmods.com/bloodborne/mods/194) | File-overlay mod manager, mod downloads, save backup/restore/viewing, launcher updates, controller remapping, trophy browser. shadPS4 folder conventions have changed across releases. | **Use design lessons**: searchable curated mod list, transaction/rollback, per-mod update alerts, save vault. No obligatory shadPS4, no default trophy unlocking, no unauthorized redistributions. |
| [Yharnam Together](https://github.com/lKaniel/bloodborne-server) | Launcher versioning/pre-release updates, self-host, server-world persistence, member HUD with vial/bullet counters, revives, long-session game state. | **Gameplay/UI ideas only** until protocol bridge exists. Dedicated-server authoritative-state protocol differs from legacy CLS and native visy P2P. |
| [CLSAMG22/BBSC](https://github.com/CLSAMG22/BBSC) + shadNet + private Seamless Hunt | Legacy bells/NP matching, accounts, signaling, gameplay hook synchronization and server transport. | **P0 interop reference**: test two-way unmodified 0.0.2 peers, password isolation, reconnect, death/lamps, both shadPS4 and BBPort. |
| [shadPS4](https://github.com/shadps4-emu/shadPS4) | Game patch metadata, per-title settings, savedata profiles and numerous community hooks. | **Compatibility/reference input**, not a required runtime. Game hashes and regional/version detection must be validated. |
| [Nexus Bloodborne](https://www.nexusmods.com/bloodborne) | Community mods, comments, version and changelog records, permission restrictions and conflicts. | **Curated opt-in manager**, not background installation of unreviewed content. Honor redistribution rights and user's mods. |
| [The Update Framework](https://theupdateframework.io/) | Signed, versioned and time-limited update metadata, target hashes, freshness and rollback-attack protection. | **Security design reference** for future trustworthy installer, not a claim that TUF is already enabled. |

## Source-level discoveries confirmed in this pass

These are more valuable than just feature claims on README pages, because the actual entry-point files exist in the other repositories:

- **Read-only Hunter parser:** [Supermedo/launcher/bbport_character.py](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_character.py) parses actual character slot bytes for name, level, six stats, Echoes, Insight, inventory/weapons and event flags. It cross-checks that character level matches the attributes sum before showing a record, rather than guessing. Inspect constraints/test fixtures, avoid scanning a live saving file; retain original GPL-2.0-or-later notice where applicable.
- **Cross-port saves:** [Supermedo/launcher/bbport_saves.py](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_saves.py) detects native/Awaken, shadPS4 old/new, bbhost and Apollo PS4 export folder variants, lists up to ten character slots and imports via staging/backup. Our current launcher only **detects** saves; the safe new work is a separate, consent-driven read-only profile page first, then proven copy/rollback.
- **Reproducible benchmark and settings comparison:** [Supermedo/launcher/bbport_benchmark.py](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_benchmark.py) distinguishes performance, visual comparison and stability soak tests, uses recorded controller steps, isolates save and shader cache under a dedicated temporary user directory and samples frame/memory/GPU metrics. Extract benchmark harness concepts only after native compatibility and performance cost review; no hidden auto-play or writes to the user's actual save.
- **Multiple game/runtime versions:** [BBLauncher/modules/version_dialog.cpp](https://github.com/rainmakerv3/BB_Launcher/blob/master/modules/version_dialog.cpp) implements an installed-version list, manual update search, cached version feed, optional changelog display and pre-release preferences. Seamless Hunt should distinguish the current *client* versions from installed games/regions and isolate rollback copies; don't assume shadPS4 binaries are valid native Windows engine updates.
- **Existing Chalice editor source:** [BBLauncher/modules/ChaliceEditor.cpp](https://github.com/rainmakerv3/BB_Launcher/blob/master/modules/ChaliceEditor.cpp) reads selected save slots, lists equipped altar glyphs, searches known dungeons and creates manual backups. This complements [BB Chalices Reborn](https://github.com/LL4nc33/BB.Chalices.Reborn); neither makes arbitrary new game geometry. Evaluate hard-coded offsets, encrypted saves and licenses before allowing writes.
- **Other mod tooling:** [BBLauncher/modules/ModManager.cpp](https://github.com/rainmakerv3/BB_Launcher/blob/master/modules/ModManager.cpp) and [ModDownloader.cpp](https://github.com/rainmakerv3/BB_Launcher/blob/master/modules/ModDownloader.cpp) exist; their dependency and data-migration behavior need a separate source audit before adapting anything.

The exact baseline upstream source version, merge direction and save parser schema must be recorded in each integration PR. Existing launcher support for saves and mods should not be silently confused with completed import or editing features.

## Product features to adopt selectively

### P0 — foundation and safety
1. Reliable native Windows binary and **real** interoperability with CLS BBSC; measured frame and network performance.
2. Account management that does not transmit plaintext credentials invisibly; actual in-game session binding, not a diagnostic-only login.
3. Immutable, signed/verified release artifacts with a source revision, file hashes, platform/version requirements, dependency and protocol compatibility.
4. Secure updater *after* signature scheme: check stable/preview channels, release notes by feature type, diff preview, download only portable verified artifacts, stage into sibling directory, close game, preserve \`user/\`, mod overlays and settings, atomically activate, automatic health checks and one-click rollback. Never download/overwrite retail game assets. Don't bypass version compatibility for network sessions.
5. Release notes/changelog should include Added / Improved / Fixed / Compatibility / Known issues, required action and migration notes. Distinguish current commit's unreleased work from a published stable build.

### P1 — player-facing quality
1. One excellent Home screen with hunter profile (when save parser verified), verified game path, exact protocol mode, server reachability and optional authoritative online count.
2. Global category search that focuses actual settings, meaningful units/explanations and strong keyboard/controller navigation.
3. Hardware assessment, suggested frame/render presets, photo comparison and *reproducible benchmark* for known areas (from Supermedo and bbhost ideas). Measure cold-boot and game FPS/p95/p99; never promise rates without data.
4. Changelog, updates and privacy-sparing opt-in upstream/mod update alerts under Tools/Updates. **Fork release updates != upstream code ideas != game patches != mods**: separate sources and consent.
5. Safe save/profile discovery and import with snapshots and differing port/source labels.
6. Source/version-aware mod compatibility manager and conflict inspection; never enable dubious gameplay cheats online.

### P2 — deeper but still practical
1. Build calculator, weapon damage, gem objectives, selectable profiles; read-only hunter detail first.
2. Optional achievements/trophies viewer from verified local data, not cheat/unlock button.
3. Native Steam shortcut or Discord presence for selected hunter and current area (consent; never leak private game/session secrets); preserve Play without overlays.
4. Chalice catalogue, tags, discoveries, validated glyph lookup, backup restore, and later specialized altar editor.
5. Text and voice language controls separately, accessibility presets for type size, color/sound subtitles, remappable controls and localization.
6. One-click offline connection/performance report with redaction and a practical "what to do next" explanation.

### P3 — optional expert/experimental
1. Save Editor, chalice mutation and complex boss/progression flags with offline format validation, exact diffs, transactional snapshots and rollback; never mutate running saves.
2. Plugin API, community mod update checks and shader-pipeline innovations only after ABI/security/licensing/driver tests.
3. LAN multi-instance hosting, debug camera, benchmarks and graphics capture in dedicated Tools, not Home.

## Upstream development workflow
1. Monitor allowlisted repos/releases at a reasonable cadence, but **never automatically import or build arbitrary upstream commits**.
2. For each potential feature capture: original source URL and commit, license, dependency tree, existing implementation overlap, expected FPS/VRAM/network benefit, save/patch conflict risk, test matrix, user-visible destination, required approval/permission.
3. Prioritize fixes affecting crashes, save integrity and party join over cosmetics or duplicate toggles.
4. Reproduce patches on an exact source snapshot; validate old and new behavior offline, then native Win64 CI, then two-machine network/graphics tests. Opt-in behind an isolated flag until proven.
5. Respect original credits, packaging and redistributable licenses. Avoid distributing game dumps, game updates, Nexus-exclusive assets and credentials.
6. Release verified source/change records and a human-readable changelog only for truly implemented and tested features.

## Red lines
- No fake online counts, uptime percentages, instant-sync guarantees or "BBSC compatible" labels from merely successful API pings.
- No updater which downloads an unsigned arbitrary ZIP and runs scripts from it; no in-place update of running binaries.
- No silent overwriting of save files or configs, no forced patch/version upgrades, no automatic mod downloads/execution.
- No automatic copying of another project's entire engine/launcher just because its README names a desirable feature.
- No bloated main screen. Expert features belong in targeted pages, searchable by intent.

## Verification checkpoint
This document is a feature radar and acceptance guide, **not** itself a release. The read-only release panel is source-committed and its corresponding tests run in GitHub Actions. A complete native Windows end-to-end visual and gaming test is still required. CI status is commit-specific; never propagate a past success to a newer commit without checking it.
