# Seamless Hunt PC: Launcher + In-Game UX Contract
Status: approved design direction from owner request, 2026-10-22. Design/implementation specification, NOT a claim that the UI has already been rebuilt.

## 1. Purpose and boundaries
Build one cohesive Bloodborne-native Windows player experience. The launcher and in-game settings should be elegant, discoverable, minimal, clear, fast, keyboard/controller accessible, and visually aligned with Bloodborne without imitating a cluttered gothic website. Do not remove any working option or downgrade networking, graphics, or gameplay while reorganizing UI.

Observed baseline 2026-10-22:
- `launcher.py`: Tk/ttk notebook in an approximately 780px window, settings tabs, log always present at the bottom, launch action, Ctrl+F setting search, per-setting tooltips.
- `gpu/shim/bbport_game_menu_pages.cpp`: more than twenty pages, including Display, Upscaler, Advanced, Party, Party network, Shared world, HUD, mouse, and gameplay rules.
- Many settings are already synchronized to `bbport.ini`; preserve and extend that authority instead of maintaining separate launcher and game values.
- Separate online transports: existing native visy party != optional legacy BBSC matchmaking. The UX must not present a network diagnostic/login ping as functioning crossplay.

## 2. Experience principles
1. First screen answers: game found? who am I? online playable? who can I play with? start game. One prominent Play action.
2. Progressive disclosure: Simple is default; Advanced reveals technical details. Never hide dangerous compatibility/security warnings.
3. Organize by player intent, not source module or environment variable. No duplicate settings in unrelated screens.
4. Self-explanatory label + one sentence explaining outcome and cost. Explain if applied immediately, next map load, or restart.
5. Presets are explicit, reversible changes to a *known compatible subset*. Remove the misleading "Everything on" premise; "Recommended" must not enable every patch.
6. Search is globally available, synonym aware, and opens the exact setting (not only its tab). Ctrl+F; safe, never indexes credentials.
7. Human-readable errors with the next step. Log files are in Support, not a permanently visible wall on Home.
8. Every destructive action shows impact, makes a recoverable snapshot where possible, confirms explicitly, and offers undo.
9. Game versions/regions: detected != verified compatible. Unsupported patch/image must be clearly explained, not silently enabled.
10. Optional gameplay cheats are solo-only by default; unknown mods and incompatible gameplay scripts must not be silently used with ordinary online players.

## 3. Information architecture for launcher
Six destinations maximum in the primary navigation, with labels suitable for English and future Russian localization:

**Home / Play**
- Bloodborne installation and verified game version/region; Auto Find / Change.
- Profile/character and save-safety status (no silent save import).
- Online status and *active connection mode* (Offline, Native Party, Seamless Hunt BBSC **only when implemented**).
- Large Play / Stop; last crash/recovery hint; compact update status.
- Optional first-run setup walks through game, device, mode, play; no developer terminology.

**Online / Friends**
- A clear network mode choice with compatibility status:
  - Solo/Offline.
  - Native party code multiplayer (existing implementation).
  - Legacy bell matchmaking on Seamless Hunt (disabled until native BBSC interoperability is genuinely tested).
- Host / Join, friends, party code, password, server selector (as applicable); never conflate BBP3 party codes with BBSC bells.
- Connection status in ordinary words; Advanced: NAT, STUN, IPv6, direct/relay, p50/p95 joins, network diagnostics.
- Credentials handled only by a secure TLS/device login flow, not plaintext upstream shadNet login disguised as a full account.
- No public claim of PS4 crossplay until tested.

**Graphics / Performance**
- Presets Recommended / Low latency / Performance / Quality / Custom. Show the exact affected settings before applying.
- Display / Rendering / Upscaling / Frame pacing / HDR / Advanced grouped within this destination.
- Hardware detection and unsupported choices disabled with explanation; avoid showing unavailable DLSS/FSR/FG as active.
- Show value AND units for FPS, render scale, VRAM, milliseconds, latency. Never use a generic "everything on".

**Game / Mods**
- Gameplay & quality of life / Controls & accessibility / Co-op rules / Mods & patches / Solo-only cheats.
- One searchable catalogue: origin, version, expected game hashes, prerequisites, conflicts, requires restart, online safety.
- Import existing mods only after review; preserve user game files and saves. Provide one-click reversible enable/disable with audit.
- Group shared world, death/revive, lamps, bosses, rewards, and PvP logically rather than scattering toggles.

**Library / Saves**
- Detected installations/regions/update versions and manual selection.
- Character/profile selection, save source (native vs shadPS4/BBPort), safe import wizard (when supported).
- Backups / restore preview / Undo and history; never auto-convert or overwrite.
- Update channel, changelog and integrity checks.

**Help / Diagnostics**
- Connection doctor, health check, crash summary, redacted shareable report, repair tools, detailed logs on demand.
- Credits, licenses, website and documentation, version/build provenance.

## 4. In-game System menu
Keep Bloodborne's original visual hierarchy and input conventions; don't introduce a foreign Windows interface inside the game.

Top-level conceptual grouping:
- Display & Performance (resolution, image quality, upscaling, HUD/FPS)
- Controls & Accessibility (gamepad, mouse, key mapping, camera, subtitles)
- Online & Party (status, host/join/leave, members, latency, privacy; mode availability truthfully labeled)
- World & Gameplay (co-op rules, deaths/revive, shared world, boss/loot settings)
- Mods & Patches (safe supported live toggles; read-only for restart-only or unsupported modifications)
- Advanced (technical rendering, transport, diagnostics, debug)

Launcher and game must use a single settings repository (supported `bbport.ini`/runtime APIs); external file changes reload on focus/game menu entry, with conflict handling and no "last writer silently wins". Show "Applies on restart" for values not safe to change live. In-game menu should avoid scrolling through twenty flat pages: categories, short subpages, breadcrumb/back and sensible focus order.

## 5. Visual language
- Deep neutral charcoal, muted slate and warm gray surfaces; restrained antique bronze for emphasis, dark crimson only for active danger/error or one primary accent.
- Type hierarchy: title, category, setting, subdued short help. Do not use ornate type for operational labels.
- Comfortable hit targets, consistent 8px spacing increments, line lengths, logical grouping and contrast.
- Minimal decoration: sparse divider strokes, subtle texture only if free of performance/accessibility regressions; no flashing, fake parchment textures, excessive bloom, gratuitous animations.
- Window scale and scroll must work at 720p and 1080p with 100%, 150%, 200% Windows display scaling, long localized labels and keyboard navigation; never clip content or hide the Play control.
- Accessible focus rings and tooltips, controller-friendly in-game navigation, hover-independent explanations.

## 6. Interaction states and examples
- Game detection: Checking / Compatible Bloodborne 1.09 / Region needs verification / Executable unsupported / Not found.
- Server checks: Offline / Connecting / Server reachable (diagnostic only) / Authenticated / Game session ready (only when joined) / Error with repair path.
- Mod state: Installed and enabled / Disabled / Requires restart / Incompatible game image / Conflicts with X / Solo-only.
- Setting actions: Recommended value, current value, what changes, requirements, reset to default, apply/restart.
- Progress always tied to actual state and validation; never show synthetic "connected" or "all clear".

## 7. Migration and engineering constraints
- Retain saved launch settings, migrated `bbport.ini` keys, existing party save partitioning and original game assets.
- Keep working legacy DLL integration opt-in while still unverified; no server process restart as part of UI work.
- Prefer incremental refactor with explicit view-model/data-driven setting metadata and a migration test suite. Do not rewrite renderer/party logic in the name of design.
- Tkinter can be used for staging while retaining a safe build, but evaluate a consistent native desktop toolkit for the long-term only after weighing package size, accessibility, deployment, and test coverage. Native app does not mean a PS4 emulator.
- The UI is a presentation layer over verified capabilities. Hide experimental features until available, not substitute a decorative fake control.

## 8. Acceptance checks
1. First-time player finds game, understands compatibility, opens Play, and locates online, graphics, controls, mods, and saves without a guide.
2. Any visible option is findable by name/common synonym in two navigation actions maximum; exact control is focused.
3. No duplicated conflicting control state between launcher and game; restart markers correct.
4. Simple mode is clean; Advanced contains technical details but all functionality stays accessible.
5. Works at 1280x720/1920x1080 and high DPI without inaccessible controls; keyboard only possible.
6. Unsupported GPU/upscaler, executable patch, network mode, mod conflicts explained before activation.
7. No crossplay claim until two-way live tests with untouched CLS 0.0.2 peers.
8. Reset, backup and undo work; no saves or account secrets leaked into logs.
9. Screenshot review in dark mode, plus usability review on actual Windows and in-game input.
10. Explicit release check: Windows compiled launcher and game tested; design doc by itself is not a completed implementation.

## 9. Implementation order
A. Freeze settings inventory, mode truth table and navigation prototype from current source (no disabled controls pretending to work).
B. Build top-level Home/Play and consolidated settings navigation, collapsing log/support details.
C. Adapt in-game pages to the same category model; shared authority and restart/status labels.
D. Search focus/synonyms, presets, conflict feedback, keyboard/HiDPI/localization support.
E. Integrate online account/BBSC capabilities only when working; validate real Windows builds and gameplay.
