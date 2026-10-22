# Hunter Hub: candidate capabilities and interface (22 October 2026)

This document extends docs/SEAMLESS_HUNT_UI_UX.md. It is a researched feature plan, NOT a claim that a save parser, editor, chalice generator, redesigned GUI, or live server census has already been implemented.

## Visual direction
Owner rejected the flat tab/card mockup. Build a polished Bloodborne-inspired interface: quiet charcoal, misty slate, restrained antique bronze, rare oxblood accent, generous negative space and a strong typographic hierarchy. No noisy gothic flourishes, gratuitous animations, permanently visible logs or huge grid of toggles. Large Play action, concise online status, selected hunter and contextual navigation on Home. Support 1280x720 and higher-DPI Windows, keyboard access, EN/RU labels and accessibility.

## Hunter profiles: P1, read-only first
Autodiscover native, shadPS4, BBPort and isolated party saves without moving or modifying them. Once a save parser is individually verified for the exact format, list actual character name, level, origin, VIT/END/STR/SKL/BLT/ARC, equipped trick weapon/firearm plus upgrades, armor, runes, echoes, insight, NG+, last known area/lantern, playtime. Unknown fields must say Unknown and never be guessed.
A build label (Skill / Quality / Arcane etc.) is a documented heuristic, not a value explicitly present in the save. Allow user-written build nicknames as separate launcher metadata, not save changes. Optional portrait uses an opt-in locally cached *in-game screenshot*; a saved appearance value is not itself a 3D render.
Selecting a character from a detected save source must not silently convert, overwrite or activate an incompatible format. Verify IDs, hashes, regions and game-not-running state. Do not distribute or collect user saves.

## First native Hunter Hub code milestone (2026-10-22)
- Added `scripts/hunter_profiles.py`: bounded, read-only parser for deciphered `userdata0000..0009` with level/stat checksum, file-size/mtime validation, UTF-16 names and conservative build labels. On unrecognized data, no fake profile is shown.
- Added `Hunters / Saves` launcher dialog that uses existing safe discovery or manual folder selection. It displays *validated* character stats and sources; no active game slot switching or save editor yet.
- Added synthetic multilingual/broken-save fixtures and CI tests on Windows and Linux. CI passing is not proof a real user's native/shadPS4/Awaken save parses correctly. Actual save comparison with in-game values remains a release gate.
- Upstream format credit: Supermedo `bbport_character.py` (GPL-2.0-or-later), Noxde. We have not redistributed a real save or copyrighted game files.

## Specific verified upstream read-only character/save implementations
Supermedo's Windows branch contains [bbport_character.py](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_character.py), a concrete read-only parser for character slot name, level, attributes, weapons, Echoes/Insight, flags/deaths and playtime. It checks the relationship between level and stat totals before reporting values. [bbport_saves.py](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_saves.py) documents the ten character slots and differing native/Awaken, modern/legacy shadPS4, bbhost and Apollo export paths, with separate staged copies and backup logic.

These are stronger implementation candidates than guessing from a save's folder name or immediately embedding a writable editor. First compare the exact parser with a redacted fixture corpus from the user's runtime/other ports and test slot ownership, old/new save formats, bounds, game version and corrupt files. Respect GPL and authorship; no copying save contents into public CI. Runtime must never edit or activate slots merely because the read-only parser has produced a character card.

## Save Editor: P3, isolated advanced tool
Review Noxde/Bloodborne-save-editor https://github.com/Noxde/Bloodborne-save-editor and Nexus https://www.nexusmods.com/bloodborne/mods/108. Source GPL-3.0; bundled integration requires license analysis. Features documented upstream: stats, inventory/items, Blood Echoes, Insight, gems/runes, boss flags, NG+, position and lantern spawn.
Stage 1: view/compare/backup only. Stage 2: explicit advanced editing with game closed, exact format detection, transactional copy-on-write, timestamp+hash backup, change diff, atomic replacement, reopen verification, one-click rollback and hostile-file fuzz tests. No live save tampering or silently using edited statistics/items/progression in public multiplayer.

## Chalice Workshop: P2 catalogue, P3 editing
Review LL4nc33/BB.Chalices.Reborn https://github.com/LL4nc33/BB.Chalices.Reborn and Nexus https://www.nexusmods.com/bloodborne/mods/342. It documents a built-in offline Community catalogue, an opt-in cached curated set, seven altar slots, searchable glyph/region/layout/rites, custom combinations, .bbc exchange and backups.
Start with offline read-only dungeon explorer and favourites, optional gem-target filters and validated altar preview. Writing crafted dungeons requires verified format/native-save support, offline eligibility, rollback and compatibility tests. A dungeon builder manipulates existing Bloodborne dungeon data; it does NOT create arbitrary new 3D maps, content or guaranteed online-public glyphs.

## Server activity panel: P1 after authoritative API check
User requests live hunter count. Supplied Fornex intake archives contain running service and binary fingerprints, NOT a verified live player-count API. Never invent numbers or equate registered users, TCP connections, open sessions, actual players and website visitors.
Design read-only aggregate endpoint after source audit and staging tests. Define separate active authenticated accounts, actively in-game hunters and joinable sessions only when measurable. Include sample timestamp, TTL/freshness, realm/client scope; cache 15-60 s, rate-limit and publish NO accounts, IP addresses or private sessions. Show Unknown/unavailable rather than synthetic 0. Keep online reachability separate from player count. Do not touch production without validation.

## Other high-return optional features
- Existing rainmakerv3/BB_Launcher https://github.com/rainmakerv3/BB_Launcher (GPL-3.0) offers mod overlay management, backup/restore, save information, input remap and patch handling; adapt concepts, never embed shadPS4 as a required runtime.
- Build planner: Bloodborne Wiki https://www.bloodborne-wiki.com/p/builds.html and Hikkaruu/BloodborneCalculator https://github.com/Hikkaruu/BloodborneCalculator describe calculators for stat investment, weapon attack ratings and boss damage; place under Hunter detail only, no auto-level editing.
- Per-character graphics/control/mod profiles, explicit Solo vs Co-op safety profiles, patch provenance/conflicts, portable modpack manifest and safe rollback.
- Read-only boss/progress checklist if data source verified; optional manual goals.
- Last-session performance/connection summary with actionable explanation, logs and redacted bundle under Help; hardware-dependent safe defaults and patches that explain restart requirements.

## Information architecture
Primary rail: Play, Online, Hunters, Graphics, Mods & Game, Tools. Tools opens Save Editor, Chalice Workshop, backups, diagnostics; save editor is never an accidental one-click action on Home.
Home is cinematic and minimal: verified current hunter with location/weapon/build and optional cover, real realm/connection status and optional verified hunter count, current play mode and one clear Play button. Advanced features remain accessible in contextual subpages and search, without bloating Home.
In-game menu and launcher share bbport.ini/runtime capability truth and synchronized settings. Current core online is visy party. Legacy CLS BBSC co-op is NOT ready until two-way live sessions are proven; never show diagnostics as working co-op.

## Priorities and acceptance
P0: dependable native Windows build + actual legacy BBSC interoperability and save safety.
P1: genuinely beautiful launcher navigation, read-only validated Hunter preview, optional honest server count, search, presets.
P2: richer Hunter detail, character-linked mod profiles, offline chalice catalogue and build planning.
P3: explicitly opt-in Save Editor and chalice mutation with game-closed, backup, diff, atomic write, restore tests and no unverified online use.
Every capability needs a real source, test fixtures, runtime validation and clear disabled/unavailable status before release. Do not distribute third-party assets or merge GPL components without obligations audit.

## Sources and evidence
Community candidates: Noxde Bloodborne Save Editor, BB Chalices Reborn, BBLauncher, Bloodborne Wiki build tools and Hikkaruu Calculator above. User's October 22 BBSC 0.0.2 Play package documents Discord status location/build and revised seamless behavior, but does not prove native port save-reader implementation. Fornex intake only proves deployed services/hashes, not active player totals.