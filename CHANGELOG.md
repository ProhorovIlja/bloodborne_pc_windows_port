- Integrated visy upstream's native Vulkan texture-GC policy with bounded VRAM budget and per-frame eviction quotas, preserving Windows Clang compatibility. GPU impact awaits device tests.
- Integrated the latest visy native Hunter editor export into Hunter Hub: read-only game save, separate editor copy, exact region/user/slot guards, and manifest path validation. Cross-port saves and editor import remain disabled pending real save acceptance.\n# Seamless Hunt PC — Changelog

This is the development changelog for the Seamless Hunt native Windows fork.
**Unreleased work below is not a downloadable, stable release.**
For actual shipped release notes, consult this fork's
[GitHub Releases](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/releases).

## [Unreleased] — feature/seamless-hunt (22 October 2026)

### Native Windows integration
- Investigated and staged an opt-in candidate native Win64 BBSC/NP adapter and pinned third-party inputs.
- Added Windows compiler/runtime compatibility and CI checks while retaining the existing native party transport.
- Prepared separate legacy BBSC module candidate builds. **Gameplay crossplay with ordinary CLS BBSC clients has not been demonstrated.**
- Fixed native BBSC retail version validation for `1.09` and `01.09`; the Windows source adapter now binds saves to the actual game-region title and native user 1, not an assumed `CUSA00207` path.
- First-time hunters without a created `SPRJ0005` folder now have a deterministic read-only future save location. Existing path components must not be files, symlinks or Windows junctions; optional `BBSC_SAVE_DIR` overrides must match that same native save, not another port. Offline Linux/Windows fixtures cover these safety rules. This is **not a tested multiplayer release**.
- Wired an **explicit, per-launcher-session legacy BBSC developer mode** into the real Windows GUI. It checks for a separately built `bbnet20.dll`, refuses concurrent native Party, requests an explicit warning acknowledgement, configures the actual upstream `BB_ONLINE`, `BB_SHADNET_SERVER`, WebAPI, and game HTTP redirect settings, and prompts for shadNet NP ID/password without persisting credentials. The TCP shadNet protocol does **not** encrypt credentials; use a unique password and trusted realm. Runtime credentials are process environment only, and a temporary game-server URL map contains no secrets. **Successful bell matchmaking and login are not yet proven on real clients.**

### Launcher and user safety
- Added read-only Bloodborne region/version, save-location, installed-mod and patch-directory discovery.
- Added Network Doctor and protocol-aware *diagnostic* Seamless Hunt checks. These do not log the game into multiplayer.
- Improved patch collision preflight, game file verification, backup safety and developer packaging boundaries.
- Added a read-only Release Center: bundled changelog, release notes from this fork's GitHub feed and manual checks. This is **not an auto-installer**.
- Added **Verify client files** in Updates: read-only SHA-256 checks for the installed native executable, bundled Python runtime, DLLs and scripts against the local `MANIFEST.json`. Missing/changed core files are distinguished from optionally customized patches. This detects damage, **not publisher authenticity**; save folders, mods and private settings are never scanned.
- Fixed Windows developer ZIP verification to permit the already-bundled `CHANGELOG.md`, with package/extracted-runtime regression coverage and a new extracted ZIP smoke gate. Future automatic installation still requires signed metadata, safe staging, and rollback.
- Added read-only Hunter/Saves browser to the existing launcher. Validated decrypted character slots can display name, level, stats, Echoes, Insight, playtime and save provenance; unknown fields remain unspecified. No slot selection or import is performed.
- Extended Hunter details with *owned* weapons and upgrade levels, optionally resolved to localized names from the player's own game archives. Active equipped slots remain unknown; weapons are never altered.
- Replaced the indiscriminate launcher "Everything on" button with a preview-and-confirm Balanced 60 FPS preset that leaves mods, XML patches, co-op rules, input, save files and online settings unchanged.
- Redesigned the start screen into a compact Hunter's Refuge with readable game/client/party status, category shortcuts, independently scrollable settings, collapsed diagnostic logs, keyboard shortcuts and no removed legacy settings.
- Hunters/Saves can pin a selected character's **read-only preview** to Home. On restart the slot is re-read and stale/invalid save data is not displayed. A pinned preview does NOT switch the save slot used by the game, and the pin can be cleared.

### Research and planned work, not shipped features
- Unified launcher and in-game settings UX, Hunter Hub character overview, optional save/chalice tools.
- Accurate server population counts (pending an authoritative, privacy-safe source).
- Signed client updates with atomic install, versioned backups, rollback, and stable/preview channels.
- Native Windows legacy CLS BBSC multiplayer interoperability, live account/session binding and offline-to-online regression testing.

### Known limitations
- No certified two-way legacy BBSC player connection from this native Windows client.
- The first read-only save parser and compact launcher are implemented but still need validation against real multi-port saves and on-device UI review; the full Save Editor and Chalice Workshop are not implemented.
- The updater can **check and display release information**, but cannot securely download/install software yet.
- Production Seamless Hunt VPS and user saves are not modified by this development branch.

## Existing upstream baseline

This fork is based on a visy-derived Windows-native Bloodborne port and retains
many upstream native-party, gameplay, rendering and launcher capabilities.
Upstream release history belongs to its original authors and should not be
misrepresented as newly invented Seamless Hunt work.

See [visy's release history](https://github.com/visy/bloodborne_pc_windows_port/releases)
and [the project status](docs/SEAMLESS_HUNT_STATUS.md) for provenance.
