# Yharnam Together | Native Windows migration, V146

Status: **developer staging only**. Neither PS4 game files nor a playable game's source are included. The exact original Bloodborne 1.09 executable and its asset tree must come from the operator's own lawful copy. Never commit game data or upload it as a GitHub Actions artifact.

## What is already native, and what is not

- **Game CPU:** The existing `bbport` Windows project runs native x86-64 Bloodborne game instructions after preparing the title's SELF/ELF into its memory layout. It is not shadPS4 CPU emulation. The program still needs a PlayStation-compatibility runtime for game-specific services.
- **GPU:** The existing renderer is Vulkan-based, with extensive code inherited from and diverged from shadPS4. Replacing this with a newly authored renderer is not required for native CPU execution.
- **Online:** The repo's `BB_PARTY` host-based party (up to four in the original base) and the Yharnam Together authenticated server protocol are different systems. **Do not enable both in one build** or assume serverless party state implements the YT five-seat server authority.
- **Five-player gameplay:** Original YT network/gameplay hooks, server grants, DBNO, invasions, rewards, join filters and all five-seat rules must be verified against a linked native Windows client. A passing C++ compile is not a multiplayer gameplay pass.
- **Build status:** Earlier V139 Windows full-EXE CI proved native client toolchain and linked executables, V142/V143 separate graphics-unit compile gates also passed. The combined V143 build and the 200-player V141 server QoS remain independent gates. Do not infer boot success, performance or security from compilation.

## Stage 0: local-only game inventory (this PR)

Run on your own PC, from the checkout:

```powershell
py -3 tools/native/v146_game_inventory.py "D:\Games\Bloodborne\CUSA03173" --output "D:\YT-private\bloodborne-inventory.json"
```

This enumerates names *locally*, but outputs **only** aggregate file counts, sizes, extension groups and presence of `eboot.bin`, `sce_sys/param.sfo`, `sce_module/libc.prx`, `dvdroot_ps4` and `dvdroot_ps4/shader`. No game bytes, user saves, real names, absolute paths, or network transfer. It does not modify the game.

For a more informative report, explicitly opt into the existing source-pinned normalized executable-image verification:

```powershell
py -3 tools/native/v146_game_inventory.py "D:\Games\Bloodborne\CUSA03173" --verify-image --output "D:\YT-private\bloodborne-verified.json"
```

The `--verify-image` option loads original scripts `prepare.py` and `game_check.py` and computes the canonical loaded-image SHA256, checks against *known clean 1.09* and *known already-patched 60 FPS* fingerprints, and reads `TITLE_ID` and the declared version from SFO. This option can take time and memory, and it still **does not check all assets, shader corruption, DLC entitlement or runtime playability**. Missing/incompatible files produce an error rather than a made-up success.

`--include-paths` explicitly includes **relative file names** if we need to diagnose region-specific layout or mods. This can reveal mod and user naming patterns, so leave it off for the first report. Never upload the whole game or any `eboot.bin`, `*.prx`, shader, `dvdroot_ps4` or save file to the public repo.

### Privacy boundaries

- The scanner has **no network code** and cannot upload anything. The JSON report can later be placed in a restricted private Google Drive folder *at the operator's choice*, after inspection.
- The GitHub Actions tests use **synthetic dummy files only**. Never configure a public workflow to fetch a private game archive or accept an unauthenticated download URL.
- GitHub private repositories are permission-gated, not secret-link shares; standard Git repositories reject blobs larger than 100 MiB and are the wrong medium for 30+ GiB game assets.
- Never store private download URLs, passwords, session cookies, PSN data, decryption keys, account tokens or save files in logs, manifests, PRs or workflow configuration.
- Retain original game binaries locally. Use source diffs, metadata, synthetic fixtures and aggregate test results to collaborate. For game-specific runtime debugging, request only a *minimal* permitted diagnostic artefact, never an indiscriminate 30+ GiB upload.

## Stage 0b: source-exact native PS4 ABI import coverage, no game bytes

The existing original `scripts/prepare.py` (on **your local machine only**) produces `out/analysis.json`, and `scripts/link_modules.py` produces `out/link.json`. Both files may include game metadata, symbol NIDs, and private file names. **Do not upload the originals** to GitHub or Drive. The scripts may also produce large linked game binaries, so never run them directly in CI with proprietary files.

Once a copy of Bloodborne has been legitimately prepared **locally** and those JSON files exist, run:

```powershell
py -3 tools/native/v147_abi_report.py --analysis out/analysis.json --link out/link.json --output native-abi-summary.json
```

The V147 converter **reads existing JSON only**, without opening `eboot.bin` or `dvdroot_ps4`. It emits only counts: original imported symbols, required module count, linked import slots, native module bindings, and unresolved imports grouped into broad host-library classes. It intentionally redacts all raw NIDs, module names, memory addresses, game titles, hashes and local absolute paths. It refuses to overwrite existing files. The missing `--link` option results in `linked_import_census=not_provided`, not a fake success.

**Do not mistake unresolved linker imports for unsupported Windows functions:** many unresolved-by-native-module imports are validly implemented by our runtime shims. A later runtime resolver/instrumentation stage must classify genuinely unimplemented imports without overstating native coverage. V147 is a safe baseline for incremental import replacement and detecting unexpected dependency changes, not a functional PS4 service or game launch test.

## Stage 0c: native Windows launcher backend isolation, V148

The real YT1.3 Windows source uses `bbport/run.py` with `bb-probe.exe`, `boot-linked.bin` and authenticated `BB_ONLINE=1`; the current Visy-derived `run.bat` is a **different native launcher** expecting `out/bbport.exe` and its standalone `BB_PARTY=host|join` implementation. The V143 native C++ build created original YT `bb-play.exe`, `bb-probe.exe`, `bb-gpu-capabilities.exe`, **not** a matching portable, game-data-backed YT package.

V148 adds a conservative early Windows batch preflight after saved launcher settings but **before any user/out/save directory is created**. Existing standalone offline and `BB_PARTY=host|join` modes still run through the same boot path. It normalizes `BB_PARTY=off/0/false/no` even when set by launcher settings, and exits code 22 rather than silently misrouting when `BB_ONLINE` is enabled, `BB_NATIVE_BACKEND=yt` is requested, `BB_NATIVE_BACKEND=offline` conflicts with `BB_PARTY`, or an unknown party mode is provided. Windows CI invokes the **real batch file** in unsupported configurations without any game assets and proves the early stop; Linux CI checks source ordering.

This guard is temporary and intentional, **not** a working YT backend. The correct follow-up is to bring the original YT Windows `run.py`, asset preparation, native network/auth module and a mutually exclusive backend selection into the final launcher, then replace the guard only after actual Protocol8 gameplay tests. Never fake compatibility by renaming `bb-play.exe` to `bbport.exe` or mixing save formats.

## Stage 0d: original YT1.3 native Windows startup, V149

The original source-pinned YT1.3 Windows launcher (Git commit `0645740a33ae21c56df3b4a0d9777086dbca6053`, `bbport/run.py` blob `1880007c0359de018bc61f46bc2a71902afe129b`) selects `bb-probe.exe` in its own `bin/` or `out/`, creates a linked boot image from your local `eboot.bin` and bundled system modules, and configures authenticated `BB_ONLINE` routing. It must **not** be confused with Visy standalone `run.bat` and its `bbport.exe`/direct `BB_PARTY` launcher.

V149 CI checks out exactly this original source and on both Ubuntu and Windows invokes the **real original** `bbport/run.py` with an intentionally empty synthetic game directory. A fake, never-executed file only tests the binary-path selection. The actual code must fail early with a clear `No eboot.bin` diagnostic, before any game binary executes, user save directory is created or live online request is issued. The smoke tests verify source Git blob SHA1 and critical original paths. **This is a missing-game/entrypoint-failure smoke, not a native Bloodborne boot or online success.**

The next meaningful packaging gate is to stage this original YT Windows `run.py`, its source-verified dependent `scripts/` and runtime redistributables alongside the exact V143-compiled YT `bb-probe.exe`. Only after that and asset-backed local tests can the client/launcher profile be safely switched to YT rather than the standalone Visy protocol. Source-only CI must never fetch or distribute the operator's 30+ GiB game copy.

## Stage 0e: read-only local mod overlay preflight, V176

The connected private game archive has a **separate clean CUSA03173** (including original `eboot.bin`, `sce_sys` and `dvdroot_ps4`), `CUSA03173-mods`, and a second independent `MODS` collection. Verified examples include MOAL (`script/talk/*.talkesdbnd.dcx`, plus .bak backups), Jump on O+L3 / Jump Attack on X+R1 (`action/`), optional memory-saver substitutions and resolution/HUD overlays. **This is an observed directory listing, NOT proof that every asset is complete or versions match. No proprietary content is checked into this repository.**

The user's own mod instructions require a single content folder per package (e.g. `MODS/Jump.../action/`, `MODS/MOAL/script/talk/`) and warn against nested `MODS/Mod Name/Mod Name/dvdroot_ps4/` structures. Keep the game's original `CUSA03173` and modded overlay entirely separate. The local V176 preflight checks **paths only**, never touches or reads the contents, never extracts archives and never guesses patch compatibility:

```powershell
py -3 tools/native/v176_mod_overlay_audit.py "D:\\Bloodborne\\MODS" --existing-overlay "D:\\Bloodborne\\CUSA03173-mods" --output "D:\\YT-private\\mod-preflight.json"
```

It enumerates mod folders, counts ignored `.bak` and uninspected ZIPs, identifies unsafe executable/script candidate files, symlinks, invalid nested `dvdroot_ps4`, case-insensitive duplicate file paths across mods and files that would replace an existing modded overlay. Default output redacts mod names, relative paths and all game content. `--include-paths` is an opt-in diagnostic for *relative path* collision examples (up to 64); don't publish it without reviewing private names. A mod being `ready_for_manual_compatibility_review` means **folder layout only**. It does NOT mean safe to activate, correct for the selected Bloodborne patch, or correct for Yharnam Together's networked gameplay.

**Safe launcher integration contract:** before enabling a new mod, check the exact executable/patch and original tree, take a save backup outside both trees, deterministically order overlays, reject conflicts until the player selects precedence, and keep script, regulation, TAE, event and network-impacting mods (notably input actions, MOAL and game logic) isolated from an authenticated multiplayer build until gameplay+save+online tests. Do not automatically apply high-risk graphics/memory substitutions just because a user uploaded them. Test the pristine game first, then each mod separately, then combinations. Do not infer compatibility between Bloodborne and Dark Souls III from similar archive names. DS3's `DarkSoulsIII.exe`, `Data*.bdt/.bhd`, `action/chr/event/map/param/script` are **reference inputs**; they are not native Bloodborne executable replacements.

## Migration gates (do them in this order)

1. **Input contract:** Validate image fingerprint, region/version, `sce_module/libc.prx`, asset-tree layout, shader readiness and mod/patch precedence from the *locally reported inventory*. Keep unknown versions blocked until independently tested; do not assume a regional directory name proves the executable.
2. **Boot parity:** The same input boots from a clean Windows native environment, once with `BB_PARTY` and `BB_ONLINE` disabled. Confirm load, Hunter's Dream, lamp travel, save/continue and error handling. Preserve a backup of saves and measure cold/hot launch times.
3. **Graphics & perf:** Integrate GPU V139 cache worker safety, V142 zero-layer safety, V143 range safety into **one** full original Windows Protocol8 build. Check 30/60/90 FPS pacing, shader stutters, GPU driver reset, idle VRAM release, multi-hour CPU/RSS/VRAM growth, controllers/mouse and DLC.
4. **Yharnam Together integration:** Introduce an explicit native YT backend profile that selects original server-owned protocol/identity, never mixes the separate serverless `BB_PARTY` wire transport with it, and fails closed on incompatible game/port/server builds. Keep real account auth, host filtering, invites, friend lists, invasions and DBNO intact.
5. **Five-player protocol/gameplay:** Verify host+4, 4+1 invasions etc. under the chosen rules, boss walls, full 5-seat enemy ownership, camera on death, spectate/free cam, damage, revives and world-event progression. Compare with upstream YT/shadPS4/bbhost/Visy/Supermedo carefully, respecting GPL/source provenance.
6. **Direct P2P release gate:** Only authorize encrypted unreliable peer-to-peer traffic after authenticated server grants, ICE candidate checks and consent freshness. Server-bound RPC, rewards, save authority and reliable/ACK traffic remain on original safe paths. Verify direct LAN and WAN across two *physical* PCs, symmetric NAT fallback, reconnect/rekey expiry and 200-player server CPU/QoS. Only afterward consider Fornex release and launcher updater.

### Upstream cross-checks

- [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc): core native Linux/Windows bbport loader and GPU/runtime model.
- [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port): Windows native game launch, standalone direct party, frame pacing, HDR and shader cache. Its serverless party is a **reference**, not a drop-in replacement for our YT server.
- [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc): Windows packaging, performance toggles, menus and input/QoL.
- [Awakenchan/LanternEngine](https://github.com/Awakenchan/LanternEngine): alternative native-game compatibility architecture; study per subsystem before adapting.
- [lKaniel/bloodborne-server](https://github.com/lKaniel/bloodborne-server): Yharnam Together server/client mechanics and gameplay compatibility.
- [shadps4-emu/shadPS4](https://github.com/shadps4-emu/shadPS4): GPU Vulkan and shader compiler fixes are candidates only when they apply to the pinned native bbport source.

### Definition of done

Passing source tests is **not** a native Windows runtime launch. Passing full Windows compilation is **not** a stable Bloodborne campaign or public online game. Every milestone requires reproducible evidence for its own layer. No real game assets may be put into public repos or CI artefacts.
