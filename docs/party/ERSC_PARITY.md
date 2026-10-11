# Seamless co-op parity: Elden Ring Seamless Co-op (ERSC) vs. bbport party co-op

Master tracking table. The model is Elden Ring Seamless Co-op (LukeYui): friends-only password sessions,
no tether, the session survives deaths and bosses, and everyone in the party progresses as if
playing solo. Update a row whenever its status changes (date + evidence). Percentages are
judgement calls: 100 = matches ERSC (or a sane BB equivalent) and is verified live; code that is
written but not verified live counts at most 60.

The player-facing summary is the **Party co-op** section of the [README](../../README.md) (How it plays /
Deaths / Coming next). Whenever a row changes what a player experiences, update that section in the
same commit: move items from "Coming next" to "How it plays" once verified live.

ERSC sources: the Nexus description (v2.0.0, pasted by the user 2026-10-11), the Nightreign mod's
description (scaling semantics), an ExitLag guide (secondary; it says 4 players where Nexus says 6, Nexus wins), the mod's docs site (https://ersc-docs.github.io/: install/settings page and FAQ, read
2026-10-11). The Nexus page (nexusmods.com/eldenring/mods/510) blocks automated fetches. ERSC
behaviour marked *(verify)* is from memory or weak sources and is not confirmed by the docs.

Last update: 2026-10-11 (integration `windows-upstream-0.5` @ 580fbd3).

## Bloodborne rule (user, 2026-10-11) - overrides ERSC where they differ

Seamless co-op must feel like a party making progress the way single-player does: no unnecessary
loading screens, summons, lost progress or respawns, and every player is free to build their
character exactly as in single-player play. Every row below is judged against this rule too: a row is
only 100% when it meets it.

## Design decisions (user, 2026-10-11) - binding

| Topic | Decision |
|---|---|
| Travel by lamp / headstone / Hunter's Mark | Ask at the lamp each time: "Travel alone" or "Travel with party" |
| Death outside a boss fight | Every player, host included, respawns at their OWN last lamp (even in another map); the others play on |
| Death during a boss fight | Limbo: spectate until the boss dies, the party wipes, or someone rests. Boss fights use a SHARED lamp: after a boss-fight death or wipe everyone respawns at the same lamp (changed 2026-10-11) |
| Echoes on death | Like single-player for everyone: echoes drop into a recoverable bloodstain |
| Item pickups and enemy drops | Instanced per player: each player can take each world item once into their own save, and every enemy drop is per player too (changed 2026-10-11) |
| NPC quest choices | Shared: the first choice made by anyone applies to the host's world and every player's save |
| Guest behind the host in story | Guest's own save catches up fully (bosses, Blood Moon, lamps, shortcuts) |
| Saves | Everyone uses a separate party save; single-player saves untouched |
| Rest at a lamp | Resets enemies for everyone (ERSC); players in boss rooms are pulled out |
| Enemy scaling default | Harder than vanilla (ERSC-like boss boosts), adjustable in Party settings |
| Death debuff ("rot") | Implemented, ON by default, Party setting to turn off |
| Chalice dungeons | Any player can perform a ritual; the party enters that dungeon together |
| Host offline | Host needed; the shared world exists only while the host plays |
| Hunter's Dream | Always shared: everyone in the Dream is in the host's Dream together |
| Cutscenes | Play for everyone in the party |
| Joining during a boss fight / cutscene | Joiner waits outside (host's last lamp / fog) until it ends |
| Party size | Max 4 players (host + 3) for now; 100% on A7 = 4 verified live |
| Friendly fire / PvP, invasions | Not part of 100%. PvP / friendly fire the host can switch on and off is a "100%+" milestone (section I) |

## Summary

| Area | Parity |
|---|---|
| A. Session & joining | 70% |
| B. World & travel | 72% |
| C. Death & respawn | 64% |
| D. Progress (anyone can progress) | 57% |
| E. Services & UI | 88% |
| F. Network & robustness | 72% |
| G. BB-specific (chalice, insight, bath) | 27% |
| H. Bloodborne rule (feels like SP in a party) | 67% |
| **Overall (unweighted mean of rows)** | **~65%** |

## A. Session & joining

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| A1 | Friends-only, password, no randoms | `cooppassword` in ersc_settings.ini (must match for all); vanilla matchmaking off | Serverless P2P with a password (stored DPAPI-protected), host address + port | 85 | party_flow; internet (NAT) untested -> F2 |
| A2 | Separate co-op save | Own save file (`save_file_extension`, e.g. .co2 vs vanilla .sl2) | Separate party save, single-player save untouched | 90 | party_flow, ingame_flow.md |
| A3 | Start / join in game | Tiny Great Pot creates the session; Effigy of Meleina joins from anywhere in the world, spawning near the host; mod items are granted on a grace rest | Title: New / Join / Continue party game; in-game System > Party: Join / Leave / Rejoin | 85 | flowlive live runs 1-4. Open: Continue needs a game restart (exit 75) |
| A4 | Join speed | Seconds after both are in the world *(verify)* | Fast join ~10 s; Continue -> summoned 23 s, fresh 53 s after the restart | 70 | Target Continue <=15 s (flowlive WIP) |
| A5 | Join any time / late joiner | Yes | Yes, with catch-up of progress + opening skip | 80 | party_catchup |
| A6 | Leave cleanly | Separating Mist leaves at any time; if the host uses it the session disbands; everyone mists out to close | Leave works (0.4 s) | 75 | Spurious "Session lost" notice (flowlive WIP); host "End party" with 2 guests untested |
| A7 | Player count | 1-6 players (host + 5) | 3 live-verified; 4 coded (party_fourp), not live (needs 4 slots) | 50 | Target 4 (user decision); 5-6 not planned |
| A8 | Settings in game | ersc_settings.ini: [GAMEPLAY] allow_invaders, death_debuffs, allow_summons, overhead_player_display; [SCALING]; [PASSWORD]; [SAVE]; [LANGUAGE] | All settings in the game's own System menu, Party pages | 90 | bbport_game_menu |
| A9 | Version check | Same mod + game version required | Party protocol version checked on join (kLinkProtocolVersion), clear reject reason | 70 | Build/patch-set mismatch beyond the protocol number not checked |
| A10 | Host toggles friendly fire / PvP | Judicator's Rulebook | None | — | Moved to the 100%+ milestone (I1) |
| A11 | Joining during a boss fight / cutscene | Joiner spawns near the host | Decision: wait outside until it ends. Not implemented | 0 | |

## B. World & travel

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| B1 | No tether / roam anywhere | All fog walls / barriers (and their teleports) removed; the whole map is open and the party may split up | Confinement walls opened; players can stand in different map blocks (stale-hit crash fixed) | 75 | travel.md §7, 146 m split held 2+ min. Real stick walk-away not tested |
| B2 | Fog / boss gates | Gone (no multiplayer fog walls) | Fog gates by pad verified | 80 | b2_seamless.md §6.8 |
| B3 | Fast travel | Warping never ends the session; players may split up, so warps are per player *(per-player warp inferred)* | Any member's lamp / headstone / mark becomes a party move with one loading screen (B2) | 85 | B2 default; 5 lamp warps in a row |
| B4 | Loading screens | One load, no rejoin | One load, guests stay clients (B1 fallback after 45 s) | 85 | b2_seamless.md |
| B5 | Independent travel (split party travels apart) | Players may split up (stated); each respawns at their own last grace | Not supported: travel always moves the whole party | 20 | Design choice; revisit after C2 |
| B6 | Scripted transitions, Hunter's Mark, headstones | n/a | All keep the session | 85 | edgetravel 6 cases |
| B7 | Mount / map waypoints | Torrent for everyone; map waypoints synchronised | n/a (no mount, no map in BB) | — | |

## C. Death & respawn

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| C1 | Guest dies alone | Respawns in the same world at the last grace THEY rested at; session not terminated | Respawns alone at a lit lamp in the party's map, keeps echoes, no bloodstain; host plays on | 80 | b2_seamless.md §6.10-6.11 |
| C2 | Host dies alone | Same rule as any player: respawns at their own last grace, the others play on | Session kept, but the WHOLE party is moved to the host's lamp (one load); guests keep HP and items | 50 | Next: host respawn without moving guests (hostdeath agent) |
| C3 | Party wipe | Everyone respawns at their last grace; session kept (boss/invasion limbo ends on a wipe) | Same; verified | 90 | §6.8 r8-r15 |
| C4 | Death penalty | Optional rot: 5 types, one picked at random per death, stacking, removed only by resting at a grace; stops one player dying endlessly while another keeps enemies from respawning | Rot (on by default, System > Party rules, host's setting counts for the party): each death -10 % max HP, max 5 stacks, cleansed by the player's own lamp / headstone use, kept across restarts; one kind (max HP), not 5. Echoes: single-player bloodstain for everyone (user decision; hostdeath work); rot is independent of it | 85 | 2026-10-11 live (balance run 4): host death -> "Rot 1/5" toast, max HP 719 -> 647, lamp warp -> cleansed, 719; guest's tag shows "deaths 1, rot 1". Guest-side death not run live; more kinds (stamina, damage) open. docs/party/balance.md |
| C5 | Spectate while dead | A death in a boss fight or invasion puts the player in limbo, spectating, until the party wipes or someone rests at a grace | None | 0 | |
| C6 | Rejoin after a crash / redirect | Rejoin by item | ~4.5 s ring to client after the world is up; crash rejoin ~30 s | 80 | §6.11 |
| C7 | Resting while others are in a boss room | They are removed from the boss room | A rest is a party move (host load), so nobody stays behind; not tested during a fight | 60 | Test during a boss fight |

## D. Progress: anyone can progress

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| D1 | Boss kills count for everyone | Yes | Yes (K10); session kept after the kill | 85 | |
| D2 | World state shared (doors, shortcuts, lamps) | Host's world; progression events completed online also progress each player's own world | Host world flags mirrored to guests live (~0.3 s); guest's own save gets C2 progress | 80 | event_flags.md §12. Visual door check pending |
| D3 | Guest actions change the host's world | Yes *(verify)* | Lamp lighting via host only. Guest levers / doors / shortcuts not routed | 30 | Next: generalise the lamp_lit request to levers/doors |
| D4 | Items & pickups | Random drops instanced per player; persistent loot (bosses, scarabs) for everyone in the area; one-time items not re-granted if already owned | Summoned awards, item-get dialog, blood gems for guests | 75 | C3 |
| D5 | Quests, NPCs, story | Progress is saved by the host's progression; quest progression "can be erratic" (FAQ advises solo + backups) | Story choices (C4), endings for summoned guests | 65 | Full NPC quest lines untested; campaign soak WIP |
| D6 | Full campaign start to credits | Playable | Not yet soaked end to end | 30 | campaign_soak (edgetravel WIP) |
| D7 | Enemy scaling | Customisable per-player scaling as a % of the vanilla formula (Nightreign doc: health_scaling=100 = vanilla per extra player); enemy and boss health / damage / posture; in 3-4 player parties big enemies' poise drops (more staggerable) | Measured: BB scales only bosses (SpEffect 7500/7501: +50 % HP and status resist, +30 poise per cooperator, damage +0); normal enemies none. Six Party settings per extra hunter (System > Party rules: boss/enemy health and damage; all six incl. poise in the overlay's Party tab and bbport.ini - the System menu is at its 12-page limit): boss/enemy HP and poise in % of the vanilla boss step, damage +%; defaults harder than vanilla (boss HP 150 %, boss damage +10 %, enemy HP 50 %); negative poise = ERSC's staggerable note. Host's values to every peer (EVENT balance), rows 7500-7503 written on each, 7503 on every normal enemy | 75 | 2026-10-11 live (balance runs 2-4): host and guest both write identical rows and put 7503 on 149/149 enemies of m24_01; sample enemy max HP 520 -> 650 (x1.25, 1 cooperator) on the host. Boss fight with the new rows and damage / poise effects not measured live. docs/party/balance.md |
| D8 | NPC dialogue / talk events synchronised | Yes | Story choices synced (C4); NPC talk with a guest present untested | 25 | Test NPC talk (Gilbert, Eileen) in party |
| D9 | A grace rest resets the world for everyone | Yes | Lamp rest = host load: enemies respawn in the host's world; guests get the refill and HP (verified) | 85 | guest_services.md §3.3 |
| D10 | Cutscenes play for the whole party | Synced talk events | Decision: everyone watches. Untested (K11 skips the clinic opening for guests) | 20 | |

## E. Services & UI

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| E1 | Rest / level / shop for guests | Everyone uses graces | Doll level-up, shops, workbench, storage; lamps + headstones (on by default); rest heals the guest | 85 | guest_services.md |
| E2 | Party HUD / names | overhead_player_display: normal / none / ping / soul level / death count | Party HUD, toasts; overhead tags with their own setting (System > Party rules > Above companions): nothing / name / name + level / name + health bar / name + deaths (and rot); level, deaths, rot in a VITALS trailer; HUD HP now from the real HP fields (+0xf8/+0xfc) | 90 | 2026-10-11 live screenshots (balance run 4): host sees "Hunter1 Lv 37", guest sees "Hunter0 deaths 1, rot 1". Ping above heads not offered (Party members page has it) |
| E3 | Map markers | Party shown on the map | n/a (BB has no map) | — | |
| E4 | Item / summon messages fast | n/a | Fast multiplayer messages, no bell/sign waits | 90 | fast join patches |

## F. Network & robustness

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| F1 | Real internet play (latency/loss) | Works over Steam | Network simulator on both transports (UDP game traffic, TCP party link) + scripted outages; party events reliable and ordered (TCP + replay cursor). Live 2026-10-11 at 60 ms/1 %, 150 ms/3 % and a 5 s total outage mid-session: bell join 5-11 s, B2 travel, guest/host deaths, boss clear, mirror parity all fine, 0 link drops | 75 | network_robustness.md §3; party-link-test netsim (300 events in order through 5 % loss + 1.5 s outage); a real 2-PC internet test still open |
| F2 | NAT traversal | Steam relay | Host: one port UDP+TCP (9307), UPnP mapping (IUPnPNAT) on by default, manual-forward hint, STUN public address in the code; guests need nothing; guest-guest hole punch with host-relay fallback; CGNAT host -> VPN | 55 | network_robustness.md §4 (2026-10-11); not tried on a real router / NAT |
| F3 | Security | n/a | Hardening + fuzzing of party events | 80 | party-security-test |
| F4 | Invasions | allow_invaders=1 enables invaders (hairpin item); no warp or rest during an invasion | None (serverless) | — | Not planned |
| F5 | Watchdog / desync recovery | n/a | Watchdog, B1 fallback; a 5 s outage mid-session survives without desync (no reconnect, client kept, mirror parity); link reconnect + event replay tested | 80 | network_robustness.md §3 (2026-10-11 outage run); party-link-test |
| F6 | Minimal anticheat | Debug flags / speed multipliers disabled in a session | None (friends only) | — | Not planned |

## G. Bloodborne-specific

| # | Feature | ERSC analogue | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| G1 | Chalice dungeons in party | Catacombs work in co-op | 2026-10-11: Pthumeru layer 1 cleared live in a party (runs c11-c15): host ritual -> guest summoned by quick join; lever + door; layer boss debug kill keeps the session (K10 both roles, guest send-home dropped); guest gets its own boss lots; the lift down to the next layer carries host and guest (y 31.5 -> 10.5, both alive); lamp exit puts both in the Dream with one load (B2 re-join). Guest ritual: chalices now shared both ways, so the host opens the altar and glyph-searches the guest's dungeon (c17: altar menu, glyph dialog and board lookup reached; the IME glyph lost its 8th char, fixed); host entry + summon into the guest's dungeon not yet verified live (c18 queued). Two old crashes not reproduced in 8 runs at 1792 MiB | 75 | c18: host enters a guest-made dungeon by glyph, party summoned |
| G2 | Insight, Messengers' bath, Insight items | — | Untested for guests | 10 | |
| G3 | Blood Moon / world phase changes | — | Untested in party (part of the soak) | 25 | |

## H. Bloodborne rule: a party that plays like single-player

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| H1 | No unnecessary loading screens | One load per warp; a death loads only the dead player | One load per party travel (B2); a host death still loads every guest | 65 | C2 (hostdeath) removes the guests' load |
| H2 | No repeated summons | Join once per play session | The session survives travel, bosses, deaths and wipes; Continue party game re-joins automatically; a crash or redirect needs a re-join (~4.5 s) | 75 | A4, C6 |
| H3 | No progress lost by anyone | Online progression also progresses your own world | Guest's own save gets kills, flags, items, story and lamps (C2/C3/C4 + mirror); full campaign not soaked; Insight / echoes for the guest partly unverified | 65 | D6 soak, G2 |
| H4 | No unnecessary respawns | Only the dead player respawns; enemies reset on a grace rest | Guest death respawns only the guest; host death respawns the whole party; enemies reset on a lamp rest only | 60 | C2 |
| H5 | Character freedom as in single-player | Every player has their own character, inventory, levels | Guests: Doll level-up, shops, workbench, storage, own inventory and consumables. Untested: runes / Memory Altar, covenants, gestures, outfits, bath shop and Insight purchases, chalice ritual by a guest | 70 | G2, guest services audit |

## I. 100%+ milestone (after every row above is 100%)

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| I1 | PvP / friendly fire the host can switch on and off | Judicator's Rulebook (host toggles friendly fire / PvP) | None | — | Not started; after 100% |
| I2 | Pings: mark a spot / see party members through walls | ERSC syncs map waypoints; overhead_player_display has a "player ping" mode | None. Plan: a ping button places a marker; every party member (and each ping) shows through walls with its distance in metres and the player's colour. Drawn in world space, either by the game's Scaleform HUD (world-to-screen transformed, like enemy HP bars / lock-on) or by the port's overlay projecting world positions with the game camera's view-projection | — | Not started; after 100%. Overlaps E2 (names over party members): reuse its projection |
| I3 | "World warper": automatic shader-cache builder | — (not an ERSC feature) | None. Plan: a solo test mode that warps through every map and lamp, walks each area, engages every enemy and boss (debug steps), triggers every cutscene, and uses every player action: each weapon's attacks in both forms (transform, charged, R2/L2), every firearm, every consumable and throwable item, every Hunter tool, every armor piece and full set worn (with each weapon held), gestures and visual effects (buffs, blood, fire, bolt, arcane). Coverage goal: as close to every pipeline the game can create as possible; logged as pipelines seen per area/action. Then it exports the shader cache as one .zip (the launcher's export format). The zip is for the player's own use or sharing with owners of the game: it is derived from game data and is never committed or published by this project | — | Not started; after 100%. Reuses the director test steps (host_stage, warps, kills) |

## Change log

- 2026-10-11: table created from the state of the integration branch at 580fbd3.
- 2026-10-11: ERSC column checked against ersc-docs.github.io (settings + FAQ) and the Nexus
  description; rows A9, A10, B7, C7, D8, D9, F6 added.
- 2026-10-11: Bloodborne rule + section H added (user). Design decisions table (user's answers); rows A11, D10 added.
- 2026-10-11: shared lamp for boss fights; per-player enemy drops; PvP host toggle as 100%+ milestone (section I, not counted in the mean).
- 2026-10-11: I2 pings through walls with distance and player colours (100%+).
- 2026-10-11: I3 world warper shader-cache builder (100%+).
- 2026-10-11: C4 85 (rot), D7 75 (enemy scaling measured + settings), E2 90 (overhead display; reusable WorldToScreen + member colours for I2) - agent/balance, docs/party/balance.md.
