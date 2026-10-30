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
