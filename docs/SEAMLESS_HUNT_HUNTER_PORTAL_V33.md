# Hunter Portal V33: unified native Bloodborne ecosystem

**2026-10-24. Status: researched, source-only prototypes, NOT live deployment.**

## Reference sites and sources

| Source | Confirmed features | Our use |
| --- | --- | --- |
| [The Hunter's Dream](https://thehuntersdream.com/about), [map](https://thehuntersdream.com/map), [profile](https://thehuntersdream.com/hunter/sec) | Site describes a world map, death/kills/boss clears, map layers, paths and hunter builds; it currently says the live map/detailed statistics are temporarily disabled | Product model, NOT their data/artwork |
| [No Dream for the Hunter](https://nodreamforthehunter.com/), [source](https://github.com/Mob100percent/NoDreamForTheHunterBB) | Notice board, player counts by area, recent deaths, messages, server stats. Maintainer says the server plans to close next month. GPL-3.0 FastAPI/SQLite backend available | Compare backend strategies; check licenses, do not copy directly |
| [Yharnam Together](https://bloodborne.seamlesscoop.dev/docs/play), [upstream](https://github.com/lKaniel/bloodborne-server) | Native team map, presence, own account/server, co-op; its map tracks teammates, not automatically every internet player | Reuse tested game/session data only |
| [BloodborneCalculator](https://github.com/Hikkaruu/BloodborneCalculator), [MugenMonkey](https://www.mugenmonkey.com/) | Build optimization, origin and weapon calculations | Candidate for accurate build planner |
| [Noxde Bloodborne Save Editor](https://github.com/Noxde/Bloodborne-save-editor) | Save backup, stats, weapons, runes, gems, bosses; GPL-3.0 | Local-only editor after real save-format acceptance and license review |
| [Peliarch randomizer](https://www.nexusmods.com/bloodborne/mods/582), [AtomFry randomizer](https://github.com/AtomFry/bloodbornerandomizerps4) | Reproducible item/enemy/boss variations and version-dependent data overlays | Offline-only candidates |
| [Nexus Bloodborne](https://www.nexusmods.com/games/bloodborne?modSort=popular) | PC Remaster, performance drawparams, better cloth, Visual Tweaks, Enhanced, Doll Rebirth, Quit to Desktop, save tools | Optional catalog, NEVER auto-merge by popularity |

The external projects' feature descriptions do not establish compatibility
with OUR Windows native runtime or game modes. Do not bundle proprietary game
assets or download/enable unknown patches automatically. No Discord login
or Discord bot dependency is planned.

## Product architecture

One maintainable native client + launcher + optional private server + public
realm + website, not five competing forks in one unstable executable.

- Launcher Home: selected hunter, verified game path/update, client version,
  network status, one prominent PLAY, suggested performance profile.
- Online: Solo, Direct Party, Legacy CLS, Public Realm and Private Realm.
  Old PS4/CLS-compatible and direct games never suddenly require a website.
- Advanced: graphics, FPS, network quality, accessible controls, mods,
  save backups, logs and troubleshooting, grouped and searchable.
- Website: Home, World Map, Activity, Hunter Profile, Tools,
  Download/Install, Documentation, Account, Server Status.
- Native account site: register with username/email/password on verified
  HTTPS website. Browser session and game entry ticket issuer are new work.
  Avoid a Discord sign-in dependency. Game server validates its own admission.
- Public site map must use a trusted game-server presence pipeline,
  not blindly trust launcher JSON or assume a client-side map implies global
  telemetry. Public presence is opt-in, coarsened and PvP-private.
- Event timeline requires real hooks for deaths, bosses and sessions;
  unsupported information displays "unavailable", never fabricated.

## Current V33 implementation

Source-only prototype in tools/poc/yharnam/web-portal-v33:

- presence.py: bounded in-memory public presence projection, at most 4096
  verified linked players, TTL, explicit trustworthy heartbeat, stale vs
  unavailable distinction, opt-in area populations and suppression for fewer
  than three players. It publishes NO names, IPs, precise coordinates or
  active PvP locations. The backend must authenticate the real observation
  adapter and validate events before using this code.
- site/index.html: original charcoal/bronze responsive portal, same-origin
  GET /api/public/v1/presence request; no fabricated real-time positions or
  amounts. GitHub Releases install/download link, succinct roadmap and
  accessible empty state. No invented website account forms.
- site/challenge.html and challenges.mjs: usable browser-only seeded
  challenge generator. Same seed+setting yields same offline run.
  No game patches, account requirements or save changes.
- Tests: Python presence and HTML safety; Node.js deterministic seed checks.

The public presence API route, trusted server adapter, game-world geometry,
live site hosting, profile/build planner, true web save editor and account
login are NOT yet implemented. The map placeholder deliberately stays empty.

## Data boundary and player privacy

Native game -> authenticated server session and area reconciliation ->
bounded trusted telemetry adapter -> private cache -> rate-limited public
read-only endpoint -> website.

Do not put account secrets in telemetry. The server controls join/leave;
event claims from altered clients need server verification. For a public
map, only show broad area counts for consented players, and suppress
groups smaller than three to reduce tracking. Exact teammate locations
require separate team-verified authorization; never reveal live opponents
to attackers during PvP. Opt-out and stale/offline handling are required.

Do not use The Hunter's Dream's map geometry/images without permission.
Either use versioned assets licensed for reuse or generate geometry from
user-owned game files in a way that does not redistribute copyrighted
content.

## Mods and performance: keep a registry, not a pile

Before importing another fork/mod, record upstream commit, provenance,
license, exact 1.09 region/build support, renderer requirements, game mode,
conflicts, security and a rollback plan. Test 1% low FPS, stutter, VRAM/RAM
soak over long sessions, recovery, network jitter and real online
compatibility. Only merge when repeated results improve the baseline.

- Candidate optional visuals: texture packs/remaster, lighting, ReShade,
  60FPS cloth and UI prompts. Large VRAM texture packs never become a
  mandatory part of the native installer.
- Offline only: game randomizers, altered save stats/items, arbitrary
  enemy tables and cheats. Keep separate saves and restore-to-vanilla.
- Multiplayer: validated native gameplay and network fixes only, with
  honest PS4/BBPort/CLS protocol compatibility tests.
- Prioritize real long-session memory/performance bugs, spectator cameras,
  Quit to Desktop, matchmaking, password correctness and session recovery
  over website decoration.

## Release and update design

The current fork already implements a read-only GitHub release checker and
release notes via scripts/update_check.py and scripts/release_center.py.
**It does not have trusted automatic installation.**

The website should contain the version, a few release highlights,
requirements, a guide and GitHub Releases link. Detailed changelogs stay
in the launcher and GitHub; no reason to manually maintain duplicates.

Before automatically applying an update, require: signed official release
manifest; pinned domain and signed SHA-256/asset length; stable/preview
channels; download in a quarantine/staging folder; verify signature before
use; preserve saves/mods/private settings; atomic swap; process-safe
restart; rollback; and a documented offline recovery path. Never pull
and execute arbitrary Nexus archives as automatic core updates.

## Release gates and order

1. Finish real Qt server and native Windows client build/test gates.
2. Build an authenticated, read-only presence adapter + public API with
   explicit privacy consent; real telemetry before a real map.
3. Implement licensed map geometry, area/lamp layers and team-only exact
   friend positions.
4. Implement username/password website registration over HTTPS, session
   security, email verification/recovery and one-time game entry tickets.
5. Add optional hunter statistics/profiles, source-verified calculators and
   local-only browser save editing with backups and strict offline mode.
6. Deliver signature-verified GitHub auto-updates with rollback, test on
   clean Windows hosts, run multiplayer interop and soak tests, then ship.

Production Fornex/CLS is not modified; no new gameplay telemetry is
silently sent to another website.
