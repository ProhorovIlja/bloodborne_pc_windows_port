# YT/CLS gameplay & mod reports, 2026-11-01

User screenshots are private; this public register records technical observations, not fixes. GitHub Issues are disabled here.

## Missing remote character
A player's HP and name can appear in the party UI while the remote hunter body is absent, reported in Hunter's Dream. Verify actor spawn/despawn, map session, role, host already loaded, travel and reconnect. Compare clean official 1.3.1 to exact experimental CLS merge, and two physical PCs to two game instances on one PC. UI membership is not actor-spawn confirmation.

## ?ActionEventInfo? is already fixed upstream
Official 1.3.1 has NameUnnamedGuestRole, which fills missing text for guest role 6 from role 7, invoked by PolishMultiplayerUi and tested by NamesTheGuestRoleTheGameLeftUnnamed. Sources:
https://github.com/lKaniel/bloodborne-server/blob/5d2305ee611ef1e03be39ff925f0da75c9a70393/emulator/src/core/bloodborne_party.cpp
https://github.com/lKaniel/bloodborne-server/blob/5d2305ee611ef1e03be39ff925f0da75c9a70393/emulator/src/core/bloodborne_party_rules.cpp
https://github.com/lKaniel/bloodborne-server/blob/5d2305ee611ef1e03be39ff925f0da75c9a70393/emulator/tests/bloodborne/test_bloodborne_ui_polish.cpp
If broken in a CLS merge, look for missing call, source drift or reloaded role table; do not reimplement.

## Other reports
CLS mixed test may reject hot join when leader already in the game. With a copied save, messenger weapons could be collected twice while Vileblood Register was absent. Confirm build SHA, save identity and reward flags before changing persistence.

## Uploaded patch XML audit
One mounted Bloodborne.xml lists 63 patch profiles, 15 enabled; DollRebirth.xml lists one enabled. All target 1.09 and include CUSA03173. User supplied two files named Bloodborne.xml, so avoid claiming both variants were parsed. Conflicting enabled write addresses:
- Performance Patch vs SSR: 0x026C4FD7
- Performance Patch vs Uncap FPS++: 0x02C0137D, 0x025629F0

Added read-only XML preflight: playable-track/audit_patch_xml.py ; Linux/Windows synthetic CI PASS:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41301335039
No user patch bytes/game files are published. Byte overlap != proven crash; disjoint patches != guaranteed compatible.

## Mod migration constraints
MOAL 2.1.0 https://www.nexusmods.com/bloodborne/mods/107 targets another native PC port; its event/talk replacements conflict with enhanced lamps, rematches and two invaders and are not active in multiplayer. Doll Rebirth 1.0.2 https://www.nexusmods.com/bloodborne/mods/617 requires BOTH talk mod and byte patch; co-op untested, saves must be backed up. Jump on L3 2.8 https://www.nexusmods.com/bloodborne/mods/156 replaces c0000.hks; variants must be mutually exclusive and input tested.

Launcher roadmap: opt-in mod registry, hash pinning and backups, file-level collisions, dependency rules, no automatic enabling; evaluate manual NG+, respec, jump options, Quit to Desktop, lamps, corpse physics, FPS/AA/LOD/effects without duplicating YT baseline. No live Fornex deploy, no screenshot or game redistribution. True 5-player gameplay still needs upstream #486 rig confirmation.
