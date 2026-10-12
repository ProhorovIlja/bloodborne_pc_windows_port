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

Last update: 2026-10-12 (agent/guestprog: D4).

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
| Party size | Max 4 players (host + 3) supported; 5-player test runs allowed (2026-10-12) to try host + 4 |
| Friendly fire / PvP, invasions | Not part of 100%. PvP / friendly fire the host can switch on and off is a "100%+" milestone (section I) |

## Summary

| Area | Parity |
|---|---|
| A. Session & joining | 86% |
| B. World & travel | 86% |
| C. Death & respawn | 86% |
| D. Progress (anyone can progress) | 83% |
| E. Services & UI | 90% |
| F. Network & robustness | 78% |
| G. BB-specific (chalice, insight, bath) | 74% |
| H. Bloodborne rule (feels like SP in a party) | 76% |
| **Overall (unweighted mean of rows)** | **~83%** |

## A. Session & joining

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| A1 | Friends-only, password, no randoms | `cooppassword` in ersc_settings.ini (must match for all); vanilla matchmaking off | Serverless P2P with a password (stored DPAPI-protected), host address + port | 85 | party_flow; internet (NAT) untested -> F2 |
| A2 | Separate co-op save | Own save file (`save_file_extension`, e.g. .co2 vs vanilla .sl2) | Separate party save, single-player save untouched | 90 | party_flow, ingame_flow.md |
| A3 | Start / join in game | Tiny Great Pot creates the session; Effigy of Meleina joins from anywhere in the world, spawning near the host; mod items are granted on a grace rest | Title: New / Join / Continue party game (a quick restart into the party game: patches, imports and the save folder are chosen at boot); in-game System > Party: Join / Leave / Rejoin; Party page values update live | 90 | 2026-10-11 flowlive: live runs fresh / continue / Leave + Join party through the real menus (ingame_flow.md 7), live value columns. Open: the restart (exit 75) stays by design (ingame_flow.md 2) |
| A4 | Join speed | Seconds after both are in the world *(verify)* | Guest world steady -> first bell 1.2 s (was 6.9 s: pre-ring spacing 0.8 s per side), world up -> summoned 10.5 s, loading gone -> summoned 6 s; Continue: host hosts 5 s after its restart | 85 | 2026-10-11 flowlive (timestamped runs, join_timing.md). Later 2026-10-11: JoinRoom -> client 0.9 s (first RTO 300 ms), client -> loading 0.8 s (prologue 0.1 s). Left: bell -> sign 2 s (0.5 s broke joins, race not found yet), the host-world load, Continue still loads the own world first; one slow sign was a waiting guest's needless load (fixed: waiting guests no longer follow same-map host travels or the host's death); the full-screen item cards seen on guests are the game's loading-screen tips; Continue -> host world in one load: on by default since 2026-10-12 (title join; 4 live 2-client runs: one load, host and guest see each other, Leave goes home; join_timing.md) |
| A5 | Join any time / late joiner | Yes | Yes, with catch-up of progress + opening skip | 80 | party_catchup |
| A6 | Leave cleanly | Separating Mist leaves at any time; if the host uses it the session disbands; everyone mists out to close | Guest Leave: the game's own OnLeave_Limit, home in 3.8 s, no "Session lost"; host Leave with 2 guests: the session ends at once (0.4 s) and both guests go home (OnLeave_Limit on host lost) | 90 | 2026-10-11 flowlive: guest Leave live (no Session lost), host End party with 2 guests live; Join party after Leave re-summoned |
| A7 | Player count | 1-6 players (host + 5) | Max 4 by user decision (host + 3): one constant (party::kMaxPartyPlayers) sizes the link slots, VITALS, HUD rows and the Party members page; the engine takes the 3rd cooperator through H1 (party_fourp). Live 2026-10-11 with 4 real clients: `cooperators 2 -> 3` on the host, every client sees all four (presence count 4), screenshots show the four together, nobody in a wall | 85 | max 4 by user decision; 100% = 4 verified live. 0.5.6 (title join): all 3 guests join on the first try (4 runs, 2 rendering + 2 headless or host-only rendering, headless-lite test mode); open: a title-joined guest never gets chrs for guests who join after it (presence count host 4 / guest 1 2 / guest 2 3 / guest 3 4, four_players.md), and the host finishes a late guest's first sync ~48 s after its load ||
| A8 | Settings in game | ersc_settings.ini: [GAMEPLAY] allow_invaders, death_debuffs, allow_summons, overhead_player_display; [SCALING]; [PASSWORD]; [SAVE]; [LANGUAGE] | All settings in the game's own System menu, Party pages | 90 | bbport_game_menu |
| A9 | Version check | Same mod + game version required | Protocol version, then the bbport build (git describe), eboot.bin, the game params (gameparam.parambnd.dcx), gameplay patches, gameplay mods, the party's installed hook set and the party rules; a mismatch is refused with what differs and what to do, shown in the party UI | 95 | version_check.md; party-link-test, test_simguest (build); live 2026-10-11: 4 clients with equal identities admitted, a guest with other party options refused at the title ("party patches differ ... use the same bbport build and party options"). Not live: two different builds |
| A10 | Host toggles friendly fire / PvP | Judicator's Rulebook | None | — | Moved to the 100%+ milestone (I1) |
| A11 | Joining during a boss fight / cutscene | Joiner spawns near the host | Decision: wait outside until it ends. The host does not ring while its boss bar is up (EMEVD 2003[11], off at 2003[12]/[15]/[53] or a load) or a cutscene plays; a bell already ringing is dropped as the fight starts; the joiner waits at the host's lamp in its own world and does not follow the host's travels in its map | 75 | 2026-10-11 flowlive live (Cleric Beast, a11_* fixtures): joiner rang 37.9 s, fight 42.4-108.9 s with no summon, summoned 111 s after the kill; earlier run: the host died in the fight, the joiner joined after the respawn. Not yet: cutscene case live |

## B. World & travel

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| B1 | No tether / roam anywhere | All fog walls / barriers (and their teleports) removed; the whole map is open and the party may split up | Confinement walls opened; players can stand in different map blocks (stale-hit crash fixed); the soak walked the host across Cathedral Ward / Great Bridge with the guest, and hopped through 9 areas | 78 | 2026-10-11: travel.md §7 (146 m split held 2+ min), campaign_soak.md rows 2-10 (no crash in 14 runs). Real stick walk-away not tested (driver ready, not run before the 0.5.2 wrap-up) |
| B2 | Fog / boss gates | Gone (no multiplayer fog walls) | Fog gates by pad verified | 80 | b2_seamless.md §6.8 |
| B3 | Fast travel | Warping never ends the session; players may split up, so warps are per player *(per-player warp inferred)* | Each lamp / headstone / Hunter's Mark asks "Travel with the party?" (game dialog, cursor on YES). YES: party move (one load, B2; a move inside the loaded map is an in-world warp for everyone). NO: only that player moves (split_travel.md) | 90 | split11-13, inworld1-2 (2026-10-11). Open: Mark choice for guests needs BB_PARTY_GUEST_MARK |
| B4 | Loading screens | One load, no rejoin | A real map change: one load (B2, guests stay clients). Every lamp warp to the loaded map (lamp menu, headstone, Mark, a host request, test steps) is a chr warp with a camera reset: no loading screen; at the lamp's own spot a no-op | 95 | inworld1-2, vis6-7 (screenshots: no load, camera behind the player). Open: Lua stage warps inside the map, same-map death respawn (hostdeath) 2026-10-12 (0.5.6): scripted stage warps (EMEVD 2003[14] / Lua WarpNextStage) to a point of the loaded map resolved (MSB region table) and moved in-world without a load (st1, `BB_PARTY_STAGE_INWORLD`, off: no real scripted warp exercised). |
| B5 | Independent travel (split party travels apart) | Players may split up (stated); each respawns at their own last grace | Guest alone: into the host's area = one load for the guest only; elsewhere (Dream) = alone host-world load, host does not load; host alone: guests stay, no load; meeting again rebuilds the chrs without a load (records exchanged; draw bit fix: no invisible guest); 3 players apart (host meets both, guests in two maps); a lone guest's world actions go to the host (worldact, checked against its own map); alone travel sets the own last lamp; guest Hunter's Mark on by default | 85 | split13-14, split21-23 (3p), vis4 (meet visible, screenshots). Off by default: enemy kill reconciliation (BB_PARTY_SPLIT_ENEMIES, not verified live). Open: boss kills while apart (D3); 2026-10-12: re-created guests drawn (root cause, split31-36), alone travel without grey screens (split32-36) 2026-10-12 (0.5.6): alone load without a forced transform; the guest's own save keeps its own spot (c7: Continue after an alone travel to Central Yharnam starts at its Dream lamp; before: Central Yharnam at (0, 0, 0), falling). |
| B6 | Scripted transitions, Hunter's Mark, headstones | n/a | All keep the session | 85 | edgetravel 6 cases |
| B7 | Mount / map waypoints | Torrent for everyone; map waypoints synchronised | n/a (no mount, no map in BB) | — | |

## C. Death & respawn

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| C1 | Guest dies alone | Respawns in the same world at the last grace THEY rested at; session not terminated | Stays a client. Lamp in the loaded map (its OWN last lamp outside a boss fight, the host's after one): revived in place and put on the lamp, NO load for anyone; peers re-create its chr. Own lamp in another map: a load for this guest only (split travel), else the host's lamp. Drops its echoes into a bloodstain (its own records). Host plays on | 90 | b2_seamless.md §6.9-6.13; 2026-10-11 hostdeath hd25/hd26: `guest: died alone: revived at its own last lamp 2412951 in the loaded map ... no load`, host `member revived in place ... re-created`, no loading screen on either game; `bloodstain recorded: echoes 5000 -> 0`. Open: the host's view of a guest re-created by a task can be a ghost (plate at the summon spot, no body; splittravel fixing the remote chr path); own-lamp death into another map refused by split travel (BB_PARTY_GUEST_DEATH_ALONE, off); 2026-10-12: the guest's stain is recoverable in its OWN world (bs4: "Acquire Blood Echoes" at the death spot after Continue), not shown in the host's world; Continue drift fixed (arr1b/arr1d: Continue at the pre-summon spot after B2 loads) |
| C2 | Host dies alone | Same rule as any player: respawns at their own last grace, the others play on | Revived ALONE at its last lamp in the loaded map, no load for anyone: its death funnel is taken, the chr revived (HP, death flags, ChrCtrl, fade-in, ChrResetRequest + Idle_wild) and put on the lamp's spawn spot; vanilla bloodstain at the death spot (pickable at once); guests stay in place, still clients, re-create the host's chr. Lamp in another map: the host loads it alone (split travel `alone`), guests stay. Every guest down too: a wipe (party respawn) | 85 | 2026-10-11 hostdeath hd10-hd20 (b2_seamless.md §6.13): Central Yharnam 2412951 and the Hunter's Dream 2102961: `host death taken: no stage request, no party move`, `host revive #1: after: hp 719`, visible on both screens, a Circle backsteps it 2.3 m, later lamp warps load and the guest follows; echoes 3000 -> bloodstain ("Acquire Blood Echoes"); other map (hd18): `the host loads it alone (the guests stay)`, guest `remote chr removed (the host travelled alone)`. Open: no death camera fade / lamp-rise animation (the host blinks to the lamp 1 s after the funnel); 3 players |
| C3 | Party wipe | Everyone respawns at their last grace; session kept (boss/invasion limbo ends on a wipe) | Same; verified | 90 | §6.8 r8-r15; 2026-10-12 hostdeath wipe5: wipe with no load for the guest (revived beside the host in-world), Continue afterwards at the own pre-summon spot |
| C4 | Death penalty | Optional rot: 5 types, one picked at random per death, stacking, removed only by resting at a grace; stops one player dying endlessly while another keeps enemies from respawning | Rot (on by default, System > Party rules; the host's setting counts for the party): each death adds a stack (max 5) of a random kind, max HP -10 % or max stamina -10 %; cleansed by the player's own lamp / headstone use; kept across restarts. Kinds 3-5 (stamina cost, rally, item discovery) coded behind BB_PARTY_ROT_ALL_KINDS=1 (off: not verified live). Echoes: single-player bloodstain for everyone (hostdeath); rot is independent of it | 95 | 2026-10-11 live: host death -> toast, max HP 719 -> 647, lamp warp -> cleansed; guest's own death: max stamina 100 -> 90, max HP 503 (70 %), toast. Kinds 3-5 chosen in live deaths ("this one: rally / stamina cost"), effect not yet observed. docs/party/balance.md |
| C5 | Spectate while dead | A death in a boss fight or invasion puts the player in limbo, spectating, until the party wipes or someone rests at a grace | Limbo while a boss bar is up (EMEVD 2003[11] HUD slots): host death taken but not revived, guest's held death outlasts its grace, until the boss dies (respawn at the host's lamp), everyone is down (wipe) or a load starts. The dead player SPECTATES: its camera follows a living party member (its dissolved chr carried 3 m behind it); peers hide its dead copy (no body, no plate) | 80 | 2026-10-12 hostdeath spec3/spec4 (Cleric Beast): host died in the fight, its screen followed the guest fighting the boss; the guest saw no host body or plate; boss killed -> host revived at its lamp. Open: guest-side spectating not run live; no member switch (follows the first living one) |
| C6 | Rejoin after a crash / redirect | Rejoin by item | ~4.5 s ring to client after the world is up; crash rejoin ~28.5 s from the restart (~32 s from the crash; title join straight into the host's world once the host's dead connection has timed out) | 80 | 2026-10-12: join_timing.md (title join waits out the sign hold: fixes a 41 s regression, 2 live runs with screenshots). The game's 25 s transport idle check is not in the transport's config block; ~15 s needs more RE |
| C7 | Resting while others are in a boss room | They are removed from the boss room | A rest is a party move; during a boss fight it is always a real load (the fight and the enemies reset, everyone is taken out of the boss room), never split travel's in-world move | 85 | 2026-10-12 hostdeath c7c (Cleric Beast): guest in the arena, host rested at lamp 2412952 -> real load for both, both at the lamp, no boss bar (screenshots). Open: a guest's own rest during a fight (alone travel) not run |

## D. Progress: anyone can progress

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| D1 | Boss kills count for everyone | Yes | Yes (K10); session kept after the kill; the guest sees the host's cleared boss (no boss, no bar) though its own save has it alive; a guest dying after / during the fight now respawns (it lay dead before) | 90 | 2026-10-11: b2_seamless.md §6.13 (watchdog live), event_flags.md §12 visual check with control run |
| D2 | World state shared (doors, shortcuts, lamps) | Host's world; progression events completed online also progress each player's own world | Host world flags mirrored to guests live (~0.3 s); guest's own save gets C2 progress; doors and boss state checked on screen | 92 | event_flags.md §12. 2026-10-11 visual with control runs: a door the host opened shows open on the guest (shut in the control); the host's cleared boss is absent for the guest |
| D3 | Guest actions change the host's world | Yes *(verify)* | Guest levers / gates / doors: the host's game gets the guest's ObjAct kick natively (logged) and the object animates in the host's world; the guest's flag changes in its copy of the host's world go to the host as EVENT `world_action` (whitelisted shortcut / world-state / key / NPC flags, host re-validates against its map, rate limit, fuzzed) and into the guest's own save; kick replay when the host's game missed it | 85 | 2026-10-11 live: lever 2411310 (host sees the gate open, screenshots) and one-way / lever doors 2411302, 2411304, 2411308 (run 16: host log `ObjAct kick (another player)`, the host's own events set 12410113/114/116); a guest's flags go as `world_action`. Lifts' state flags excluded (their own sync). Not run: ladder, lift ride, illusory wall |
| D4 | Items & pickups | Random drops instanced per player; persistent loot (bosses, scarabs) for everyone in the area; one-time items not re-granted if already owned | Boss rewards / key items for everyone present (C3), item-get dialog, blood gems. Enemy drops per player, ON by default: every player's game rolls each enemy's drop and keeps its whole own roll (guests too). Instanced world treasure for guests coded but opt-in (BB_PARTY_GUEST_PICKUP=1: no treasure record is created on a guest yet) | 80 | 2026-10-12 live, fresh characters on pristine saves: the host's kill of a clinic enemy rolled a drop on both games (same enemy handle), the guest took its own copy - "Iosefka's Blood Vial" (not a guest-drop item in vanilla) - with the default build (run 45, screenshots of both windows). Treasure for guests: open |
| D5 | Quests, NPCs, story | Progress is saved by the host's progression; quest progression "can be erratic" (FAQ advises solo + backups) | Story choices (C4), endings for summoned guests; soak: boss flags of 8 bosses in the guest's own save, late joiner catches up bosses, cutscenes for everyone (Blood Moon, Gehrman refusal, Mergo's arena entry, Amelia's skull, ending); a guest's NPC talk choice lands in the host's world and the guest's own save | 78 | 2026-10-11 campaign_soak.md. The host did not save a guest's NPC choice (fixed: save request, Continue re-check not run); cutscene double-play on clients root-caused, fix opt-in (BB_PARTY_STORY_DEDUPE=1) |
| D6 | Full campaign start to credits | Playable | Soaked new game -> clinic -> Dream -> Central Yharnam -> Cleric Beast -> Gascoigne -> Cathedral Ward -> Amelia -> skull (night) -> Forbidden Woods -> Rom -> Blood Moon -> Nightmare Frontier -> Mensis (Micolash, Mergo's Wet Nurse) -> Gehrman -> ending B + staff roll on host and guest, Continue between every run | 82 | 2026-10-11 campaign_soak.md (2 players end to end; 3 players: travel chain, row 14; test-step travel and kills, not real play) |
| D7 | Enemy scaling | Customisable per-player scaling as a % of the vanilla formula (Nightreign doc: health_scaling=100 = vanilla per extra player); enemy and boss health / damage / posture; in 3-4 player parties big enemies' poise drops (more staggerable) | Measured: BB scales only bosses (SpEffect 7500/7501: +50 % HP and status resist per cooperator, damage +0; the rows' +30 poise is inert: the engine counts changeSuperArmorPoint only with stateInfo 155). Six settings per extra hunter (System > Enemy scaling, overlay Party tab, bbport.ini); defaults harder than vanilla (boss HP 150 %, boss damage +10 %, enemy HP 50 %, boss poise made real); negative poise = ERSC's staggerable note. Host's values to every peer; rows 7500-7503 written on each; 7503 on normal enemies, never on the 34 boss + 66 chalice boss entities | 95 | 2026-10-11 live (Cleric Beast, 1 cooperator): boss HP 5277 / 5277 on host AND guest (vanilla 4523), poise bonus +30 counted by the engine's sum, damage A/B 0 vs 100 %: hits 61-239 vs 216-534; enemies 520 -> 650; Enemy scaling page with six sliders screenshotted in the game's System menu. 2 cooperators (7501) not runnable: the test pool is 2 clients. Stagger frames not measured. docs/party/balance.md |
| D8 | NPC dialogue / talk events synchronised | Yes | Guests talk to world NPCs (IsClientPlayer answered 0 for world talk scripts); quest flags the talk sets go to the host's world and the guest's own save (world_action npc_quest, set and clear); NPC quest sync to every guest's save on by default (shared quest choices, user decision) | 70 | 2026-10-11 live: Gilbert (talk prompt, dialogue), Iosefka at the clinic door: guest `set 1143 72410337 12410739 (npc_quest)` -> host `slot 1 changed the host's world ... 1143=1 72410337=1`. Cathedral Ward run: Oedon Chapel Dweller -> host 72400310=1, Eileen -> host 72400520=1. Next: a quest choice with an item gift, Alfred |
| D9 | A grace rest resets the world for everyone | Yes | Lamp rest = host load: enemies respawn in the host's world; guests get the refill and HP (verified) | 85 | guest_services.md §3.3 |
| D10 | Cutscenes play for the whole party | Synced talk events | Host-triggered scenes play for every guest (C4 live mirror); NEW: a scene a guest's own event plays in the host's world goes to the host (EVENT story_up), the host plays it and sends it to every guest; the triggering guest keeps its own copy | 70 | 2026-10-12 live (test hook `up:21000040`): host and guest played the same remo at the same moment for 54 s; the party HUD panel and name tags now hide while a cutscene plays and come back after it (screenshots of both instances: no panel during the scene, panel and the partner's tag in place after). A real guest-triggered story event not run |

## E. Services & UI

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| E1 | Rest / level / shop for guests | Everyone uses graces | Doll level-up, shops, workbench, storage; lamps + headstones (on by default); rest heals the guest | 85 | guest_services.md |
| E2 | Party HUD / names | overhead_player_display: normal / none / ping / soul level / death count | Party HUD, toasts; overhead tags with their own setting (System > Party rules > Above companions): nothing / name / name + level / name + health bar / name + deaths (and rot), in each member's colour (HUD panel names too), above the game's own phantom label; a tag only for a chr the game has here this tick, alive, not disabled, on our map, from a fresh board (no floating bars); level, deaths, rot in a VITALS trailer; HUD HP from the real HP fields | 95 | 2026-10-11 live screenshots: "Hunter1 Lv 37", "Hunter0 deaths 1, rot 1", coloured tag above the game's label; tag gating unit-tested (party-hud-test) and logged (`tag X hidden: why`). The game's own floating plate over a stale host-side copy belongs to split travel / 4p (docs/party/split_travel.md) |
| E3 | Map markers | Party shown on the map | n/a (BB has no map) | — | |
| E4 | Item / summon messages fast | n/a | Fast multiplayer messages, no bell/sign waits | 90 | fast join patches |

## F. Network & robustness

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| F1 | Real internet play (latency/loss) | Works over Steam | Network simulator on both transports (UDP game traffic, TCP party link) + scripted outages; party events reliable and ordered (TCP + replay cursor). Live 2026-10-11 at 60 ms/1 %, 150 ms/3 % and a 5 s total outage mid-session: bell join 5-11 s, B2 travel, guest/host deaths, boss clear, mirror parity all fine, 0 link drops | 75 | network_robustness.md §3; party-link-test netsim (300 events in order through 5 % loss + 1.5 s outage); a real 2-PC internet test still open |
| F2 | NAT traversal | Steam relay | Host: one port UDP+TCP (9307), UPnP on by default, manual-forward hint, STUN address in the code. **No port: UDP hole punching** - each guest's code `BBG1-...` (its STUN endpoint) to the host (*Add a guest code*), the host punches, the party link falls back to a reliable UDP stream on the same port (`party_rudp`), the game's UDP shares the mapping. Guest-guest punch with host relay. Symmetric NAT / CGNAT on both sides cannot be punched -> another host or a VPN; member relay considered, not built | 75 | 2026-10-11: network_robustness.md §3b/§4; live NAT-sim run (`nat=1`, no TCP listener): link over UDP 0.6 s after the punch, bell join, B2 travel; party-link-test rudp + NAT cases. No real router tested |
| F3 | Security | n/a | Hardening + fuzzing of party events | 80 | party-security-test |
| F4 | Invasions | allow_invaders=1 enables invaders (hairpin item); no warp or rest during an invasion | None (serverless) | — | Not planned |
| F5 | Watchdog / desync recovery | n/a | Watchdog, B1 fallback; a 5 s outage mid-session survives without desync (no reconnect, client kept, mirror parity); link reconnect + event replay tested | 80 | network_robustness.md §3 (2026-10-11 outage run); party-link-test |
| F6 | Minimal anticheat | Debug flags / speed multipliers disabled in a session | None (friends only) | — | Not planned |

## G. Bloodborne-specific

| # | Feature | ERSC analogue | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| G1 | Chalice dungeons in party | Catacombs work in co-op | 2026-10-11 (0.5.2): Pthumeru layer 1 cleared live in a party (c11-c15, c20, c22, c25, c26): summon by quick join; lever + door; layer boss kill keeps the session (K10 both roles); each player's own boss loot (screenshots: item-get on both); the lift carries both (31.5 -> 10.5); the guest called the lift with the top lever (c22, c25; not in c26b); lamp exit puts both in the Dream with one load. Any player's ritual: chalices shared both ways; the host's altar offers "Enter the party's dungeon" for a guest's dungeon, also one from an earlier session (no glyph typing; c20: host entered, guest summoned, boss, loot, lift). Not verified: the one-press prompt walk (BB_PARTY_ALTAR_AUTO, off by default), the bottom lift lever, the guest's single load with its own copy, layer 2 and deeper | 85 | layer 2 walk; one-press entry live; bottom lever |
| G2 | Insight, Messengers' bath, Insight items | — | Boss Insight (native +1 + director N-1); NEW: a host's non-boss Insight (first encounter, story) also goes to every guest present; Insight items white-enabled; Bath Messengers incl. the Insight shop open to guests (own echoes / Insight / stock) | 55 | Insight-shop purchase by a guest verified live earlier (guest_services.md 5: Insight 6 -> 5 in the guest's own save); encounter / story Insight for guests unit-tested, not run live |
| G3 | Blood Moon / world phase changes | — | Blood Moon live in a party (13201803, cutscene 32000000 on host and summoned guest, time of day into the guest's own save, event warp followed); evening -> night by Amelia's skull (12401803, cutscene 24000030 on both, host flag saved); a guest behind gets the host's time of day at the next summon | 82 | 2026-10-11 campaign_soak.md rows 5b, 7b, 13, 13b. The time-of-day catch-up only moves upward |

## H. Bloodborne rule: a party that plays like single-player

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| H1 | No unnecessary loading screens | One load per warp; a death loads only the dead player | Same-map moves without a load (in-world); a lone traveller's load only for that player; one load per party travel | 86 | inworld1-2, split13-14; hostdeath hd10-hd20: a host death in the loaded map loads nobody (revive in place), in another map only the host. Open: a guest's lone death respawn is still a death load (the revive could serve it too) 2026-10-12 (0.5.6): stage warps inside the loaded map without a load (off by default, st1). |
| H2 | No repeated summons | Join once per play session | The session survives travel, bosses, deaths and wipes; Continue party game re-joins automatically; a crash or redirect needs a re-join (~4.5 s); after Leave, Join party re-summons (2026-10-11 flowlive: NP context re-registered, signaling resolve retried); a guest's join is ~12 s from its world to the host's (join_timing.md 2026-10-11) | 75 | A4, C6 |
| H3 | No progress lost by anyone | Online progression also progresses your own world | Guest's own save gets kills, flags, items, story and lamps (C2/C3/C4 + mirror); full campaign not soaked; Insight / echoes for the guest partly unverified | 65 | D6 soak, G2 |
| H4 | No unnecessary respawns | Only the dead player respawns; enemies reset on a grace rest | Only the dead player respawns (host revive in place, guest lone respawn); a wipe respawns everyone; enemies reset on a lamp rest only | 80 | C2 (hostdeath 2026-10-11) |
| H5 | Character freedom as in single-player | Every player has their own character, inventory, levels | Guests: Doll level-up, shops (vials, bullets), workbench, storage, mirror, dress-up, Insight shop, own inventory and consumables; world NPCs (D8); world treasure (D4, instanced). Static audit (world_actions.md 8): Memory Altar t210690 has no client test; equipment / outfits / gestures are menu-local. Chalice ritual by a guest stays host-only (G1) | 75 | Talk-script IsClientPlayer scan of every talkesdbnd; not run live: Memory Altar, covenants |

## I. 100%+ milestone (after every row above is 100%)

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| I1 | PvP / friendly fire the host can switch on and off | Judicator's Rulebook (host toggles friendly fire / PvP) | None | — | Not started; after 100% |
| I2 | Pings: mark a spot / see party members through walls | ERSC syncs map waypoints; overhead_player_display has a "player ping" mode | None. Plan: a ping button places a marker; every party member (and each ping) shows through walls with its distance in metres and the player's colour. Drawn in world space, either by the game's Scaleform HUD (world-to-screen transformed, like enemy HP bars / lock-on) or by the port's overlay projecting world positions with the game camera's view-projection | — | Not started; after 100%. Overlaps E2 (names over party members): reuse its projection |
| I3 | "World warper": automatic shader-cache builder | — (not an ERSC feature) | None. Plan: a solo test mode that warps through every map and lamp, walks each area, engages every enemy and boss (debug steps), triggers every cutscene, and uses every player action: each weapon's attacks in both forms (transform, charged, R2/L2), every firearm, every consumable and throwable item, every Hunter tool, every armor piece and full set worn (with each weapon held), gestures and visual effects (buffs, blood, fire, bolt, arcane). Coverage goal: as close to every pipeline the game can create as possible; logged as pipelines seen per area/action. Then it exports the shader cache as one .zip (the launcher's export format). The zip is for the player's own use or sharing with owners of the game: it is derived from game data and is never committed or published by this project | — | Not started; after 100%. Reuses the director test steps (host_stage, warps, kills) |

## Change log

- 2026-10-12 (splittravel, 0.5.6): B4 94 -> 95 (scripted stage warps in the loaded map, off), B5 82 -> 85 (Continue after an alone travel keeps the own save spot, c7), H1 85 -> 86; B 85 -> 86.
- 2026-10-12 (overlay): C6 evidence updated (title join after a crash: 41 -> 28.5 s); party-link-test NAT case tolerant of load.
- 2026-10-11 (overlay, 0.5.2): D2 85 -> 92 (door opened by the host seen open by the guest, control shut); C6 stays 80 (transport RE started, experimental off).
- 2026-10-11 (overlay): F2 55 -> 75 (UDP hole punching with guest codes, reliable UDP link, NAT sim live), D1 85 -> 90 (guest death after a boss fixed; boss state visual), D2 80 -> 85 (boss visual; doors inconclusive), C6 80 (profiled; the 26 s hold remains).
- 2026-10-11: table created from the state of the integration branch at 580fbd3.
- 2026-10-11: ERSC column checked against ersc-docs.github.io (settings + FAQ) and the Nexus
  description; rows A9, A10, B7, C7, D8, D9, F6 added.
- 2026-10-11: Bloodborne rule + section H added (user). Design decisions table (user's answers); rows A11, D10 added.
- 2026-10-11: shared lamp for boss fights; per-player enemy drops; PvP host toggle as 100%+ milestone (section I, not counted in the mean).
- 2026-10-11: I2 pings through walls with distance and player colours (100%+).
- 2026-10-11: I3 world warper shader-cache builder (100%+).
- 2026-10-11: D7 95 (poise made real, chalice boss entities, Enemy scaling page screenshot), E2 95 (tags only for live chrs, member colours), C4 rot kinds 3-5 behind a switch - agent/balance.
- 2026-10-11: C4 95 (2 rot kinds, guest death live), D7 90 (Cleric Beast live on both peers, damage A/B), Enemy scaling page back (MaxPages 16, live), HP offset +0xf8 fixed in party_b2 / guestsvc / phantom - agent/balance.
- 2026-10-11: C4 85 (rot), D7 75 (enemy scaling measured + settings), E2 90 (overhead display; reusable WorldToScreen + member colours for I2) - agent/balance, docs/party/balance.md.
- 2026-10-11: A7 (4 players live with 4 real clients on 2 of 3 runs, 85) and A9 (build / params / party hook fingerprint, live mismatch refusal, 95), agent/sixp.
- 2026-10-11: D5 78, D6 82, G3 82 (Mergo killed, Amelia's skull night switch, NPC choice host save) - agent/edgetravel.
- 2026-10-11: B1 78, D5 70, D6 75, G3 75 - campaign soak new game -> end credits (2 players), Blood Moon catch-up; agent/edgetravel, docs/party/campaign_soak.md.
- 2026-10-11: D6 note (3-player travel soak), gather to the host's map; summary D 64 - agent/edgetravel.
- 2026-10-11: B3 90, B4 92, B5 70, H1 78 (splittravel): the lamp / headstone / Hunter's Mark question, alone travel for host and guests, same-map moves without a loading screen (split_travel.md).
- 2026-10-11 (guestprog): D3 80, D4 75, D8 75, G2 50, H5 75 - guest world actions, NPC talk, instanced pickups, encounter Insight, Blood Moon catch-up (world_actions.md).
- 2026-10-11: C1 85, C2 85, C5 50, H1 85, H4 80 (agent/hostdeath, b2_seamless.md §6.13): host revived in place at its lamp (guests stay), host death to another map alone, boss-fight limbo for host and guest, guest bloodstain.
- 2026-10-11: B4 94, B5 78 (splittravel, 0.5.2): same-map hook for every lamp warp, camera reset, the invisible-guest draw bit, meets exchange records, 3 players apart, worldact for apart guests; enemy reconciliation off by default.
- 2026-10-11 (guestprog, 0.5.2): D3 85, D4 75 (instanced treasure / full guest drops opt-in), D10 65 (guest-triggered cutscenes for the party), G2 55; gate and time-of-day catch-up opt-in.
- 2026-10-12 (guestprog): D10 70 - party HUD hidden during cutscenes (live). Guest pickup / drop opt-ins stay off: the live fixture could not reach a treasure or a live enemy reliably (not verified).
- 2026-10-12: B5 (splittravel): invisible re-created guest fixed at the root (STEP_Create creates phantoms hidden; a rewound chr is shown as InGameStart does), the grey-screen regression fixed (summoned placement written for every host-world load), shot.py --grey detector.
- 2026-10-12: C1 90 -> 85 (agent/hostdeath): a guest's bloodstain is not shown in the host's world (stain1-3); Continue drift still open (pin behind a switch).
- 2026-10-12: C1 85 -> 90 (agent/hostdeath): guest Continue drift fixed (B2 arrival by the host's own travel + chr warp), guest bloodstain recoverable in its own world.
- 2026-10-12 (hostdeath): wipes after split travel: member_down op (clash with split's dead-enemies op), dead guest revived on an in-world follow; no forced transform in the dead follow / solo re-join.
- 2026-10-12: C5 50 -> 80 (agent/hostdeath): spectate in boss-fight limbo (camera follows a living member, dead copy hidden on peers).
- 2026-10-12: C7 60 -> 85 (agent/hostdeath): a rest during a boss fight is a real load; bell join waits for the host's map, gather to the lamp nearest the host.
- 2026-10-12 (guestprog): D4 80 - per-player enemy drops on by default (live on fresh characters); guest treasure stays opt-in.
