# Seamless Hunt PC — Changelog

This is the development changelog for the Seamless Hunt native Windows fork.
**Unreleased work below is not a downloadable, stable release.**
For actual shipped release notes, consult this fork's
[GitHub Releases](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/releases).

## [Unreleased] — feature/seamless-hunt (22 October 2026)

### Native Windows integration
- Investigated and staged an opt-in candidate native Win64 BBSC/NP adapter and pinned third-party inputs.
- Added Windows compiler/runtime compatibility and CI checks while retaining the existing native party transport.
- Prepared separate legacy BBSC module candidate builds. **Gameplay crossplay with ordinary CLS BBSC clients has not been demonstrated.**

### Launcher and user safety
- Added read-only Bloodborne region/version, save-location, installed-mod and patch-directory discovery.
- Added Network Doctor and protocol-aware *diagnostic* Seamless Hunt checks. These do not log the game into multiplayer.
- Improved patch collision preflight, game file verification, backup safety and developer packaging boundaries.
- Added a read-only Release Center: bundled changelog, release notes from this fork's GitHub feed and manual checks. This is **not an auto-installer**.
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
- The full redesigned launcher, read-only save parser, full Save Editor and Chalice Workshop are not yet implemented.
- The updater can **check and display release information**, but cannot securely download/install software yet.
- Production Seamless Hunt VPS and user saves are not modified by this development branch.

## Existing upstream baseline

This fork is based on a visy-derived Windows-native Bloodborne port and retains
many upstream native-party, gameplay, rendering and launcher capabilities.
Upstream release history belongs to its original authors and should not be
misrepresented as newly invented Seamless Hunt work.

See [visy's release history](https://github.com/visy/bloodborne_pc_windows_port/releases)
and [the project status](docs/SEAMLESS_HUNT_STATUS.md) for provenance.
