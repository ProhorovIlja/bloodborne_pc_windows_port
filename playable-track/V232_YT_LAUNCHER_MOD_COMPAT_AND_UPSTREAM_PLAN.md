# V232: safe Yharnam Together v1.3.1 launcher mods preflight and source review

2026-11-01. Draft playable PR #85. NO production deploy, no public
game/mod/saves or original executable. This is a read-only companion
module that can be wired into the EXISTING launcher, not a second launcher.

## Grounded upstream functionality, to avoid reimplementing it

Official `lKaniel/bloodborne-server` **v1.3.1** is pinned at
`5d2305ee611ef1e03be39ff925f0da75c9a70393`.
Its `bbport/scripts/mods.py` already implements:
- per-mod `discover`, `selected`, `content_root`, `mod_files`;
- recognized nested `dvdroot_ps4`/CUSA wrappers and case-insensitive paths;
- `mods.json` order and disabled mods;
- optional adjacent `CUSA03173-mods` base overlay before user-selected mods;
- layered game views, with later mods winning per **whole file**;
- safety guards against executable patch/DLL replacement and symlinks.

Its launcher/docs already offer graphics, input, cheats, mods,
external XML patches and launch options. Do NOT duplicate those panels.

## NEW source-only implementation

New `playable-track/yt_launcher_mod_conflicts_v232.py` reuses the
**actual original loader's** selected list, mod layout and target
enumeration (imports upstream `bbport/scripts/mods.py`).

It DOES NOT install/uninstall mods or change the user's original game.
It reports:
- exactly which enabled layer wins the same game-relative file target;
- case-insensitive path collisions and precedence of the adjacent
  `CUSA03173-mods` base overlay;
- extra risk for overlapping gameplay `param`, `event`, `script`
  and `map` files (binary archives are NOT merged);
- fail-closed rejection of invalid/modifying file layouts, per-layer
  duplicate casefold targets, symlinks, executable/system paths,
  missing/invalid mod profiles and excessive file counts;
- optional `--fingerprint-gameplay`: stable streaming SHA-256 of
  the **effective final winning gameplay override file contents**
  and normalized relative paths, independent of mod *display names*.
  It has a 2 GiB bounded read budget, reads in 1 MiB chunks and
  checks file size/mtime for mutation while hashing.
  Cosmetic-only changes do not affect this gameplay fingerprint.

This hash does **not** include the retail game/patch binaries,
native code hooks, full client build, server protocol or all
content that can influence multiplayer. It is a *candidate input*
for a later authenticated compatibility handshake, NOT a
working released YT session admission check and NOT proof of mod
safety or legal use.

Example for a PRIVATE/local installation:

```bash
python playable-track/yt_launcher_mod_conflicts_v232.py \
  --upstream-mods-script /PRIVATE/YT-1.3.1/bbport/scripts/mods.py \
  --mods-dir /PRIVATE/YT-1.3.1/bbport/mods \
  --profile /PRIVATE/YT-1.3.1/mods.json \
  --base-overlay /PRIVATE/CUSA03173-mods \
  --fingerprint-gameplay \
  --output /PRIVATE/yt-preflight-local.json
```

`--profile`, `--base-overlay` and `--fingerprint-gameplay` are
optional. The report is private by default. Never automatically send
it, original paths or mod assets to a public error tracker.

## Tests

`test_yt_launcher_mod_conflicts_v232.py` uses INVENTED mod
files and the pinned real upstream 1.3.1 `mods.py`. It covers:
load precedence (base overlay first), alternate casefold paths,
gameplay and cosmetic collisions, disabled mods, whole-file winner,
unsafe path rejection, duplicate game targets within one mod,
hash sensitivity to gameplay changes, hash insensitivity to
cosmetic changes and deterministic repeatability.

GitHub Actions matrix on **Windows and Ubuntu PASS**:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41333733614
No owner retail data, private installed mods or game addresses in CI.

## Newly identified useful PUBLIC designs

`visy/bloodborne_pc_windows_port` (GPL-3.0, reviewed README and
`docs/party/network_robustness.md`, `version_check.md`,
`save_safety.md` as of commit
`79889e01f173ac656fb969255ee2d921b13f0e99`):
- Direct peer game UDP, NAT hole punching, host relay fallback;
  reliable ordered party control over TCP or reliable UDP;
- source-defined simulated latency, jitter, loss, reordering,
  disconnects and outages, with event cursor and deduplication;
- host/guest compatibility identity covering port/build, game
  executable, game params, patches, mods, hook set, party rules;
- party save isolation, atomic pre-session snapshots and recoverable
  undo with verification.

These are **source-backed architecture/research references**, not
evidence that this port and YT can talk to each other. Do not
copy GPLv3 implementation into the current YT GPL-2.0-or-later
branch without an explicit compatible license plan and attribution.

BBHost's released 0.2.20 notes include GPU particle fixes and
performance analysis, but those metrics are for its own engine,
not transferable guarantees. Measure YT separately.

## Deployment/integration acceptance

1. Hook the read-only JSON into YT's existing Mods UI so it shows
   severity, winning mod, and disabled alternative before launch.
   No automatic overwrite or auto-enable of experimental patches.
2. Reconcile XML executable patch conflicts separately, using
   existing `audit_patch_xml.py`; don't assume file-level and
   executable-byte overlaps are the same problem.
3. Create reversible per-session mod presets with explicit
   multiplayer-compatible gameplay preset and cosmetic-only overrides.
4. Before admitting a player, compare a complete authenticated
   protocol/game/patch/hook/params identity PLUS the new effective
   gameplay override hash, not this hash alone.
5. Benchmark first boot/game load, mean/p95 frame time, server
   CPU and bandwidth, join time, P2P relay rate, crash and
   save-restore success on repeatable two-PC/five-client tests.
6. Only after actual player captures and tests, implement a
   compatibility adapter between YT and BBHost/BBPort. Reports
   of CLS experiments are not a confirmed protocol contract.

Current PR #85 still does NOT contain shipping authenticated UDP
transport or five-player release. The separate no-EBOOT original-game
Windows native port remains PR #84.
