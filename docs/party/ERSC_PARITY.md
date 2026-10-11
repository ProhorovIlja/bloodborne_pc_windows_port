# Seamless co-op parity: Elden Ring Seamless Co-op (ERSC) vs. bbport party co-op

Master tracking table. The model is Elden Ring Seamless Co-op (LukeYui): friends-only password sessions,
no tether, the session survives deaths and bosses, and everyone in the party progresses as if
playing solo. Update a row whenever its status changes (date + evidence). Percentages are
judgement calls: 100 = matches ERSC (or a sane BB equivalent) and is verified live; code that is
written but not verified live counts at most 60.

ERSC sources: the mod's docs site (https://ersc-docs.github.io/: install/settings page and FAQ, read
2026-10-11). The Nexus page (nexusmods.com/eldenring/mods/510) blocks automated fetches. ERSC
behaviour marked *(verify)* is from memory or weak sources and is not confirmed by the docs.

Last update: 2026-10-11 (integration `windows-upstream-0.5` @ 580fbd3).

## Summary

| Area | Parity |
|---|---|
| A. Session & joining | 78% |
| B. World & travel | 72% |
| C. Death & respawn | 57% |
| D. Progress (anyone can progress) | 55% |
| E. Services & UI | 82% |
| F. Network & robustness | 48% |
| G. BB-specific (chalice, insight, bath) | 27% |
| **Overall (unweighted mean of rows)** | **~62%** |

## A. Session & joining

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| A1 | Friends-only, password, no randoms | `cooppassword` in ersc_settings.ini (must match for all); vanilla matchmaking off | Serverless P2P with a password (stored DPAPI-protected), host address + port | 85 | party_flow; internet (NAT) untested -> F2 |
| A2 | Separate co-op save | Own save file (`save_file_extension`, e.g. .co2 vs vanilla .sl2) | Separate party save, single-player save untouched | 90 | party_flow, ingame_flow.md |
| A3 | Start / join in game | Tiny Great Pot (open lobby), Effigy of Malenia (join), Challenger's Lynchpin (join as invader) | Title: New / Join / Continue party game; in-game System > Party: Join / Leave / Rejoin | 85 | flowlive live runs 1-4. Open: Continue needs a game restart (exit 75) |
| A4 | Join speed | Seconds after both are in the world *(verify)* | Fast join ~10 s; Continue -> summoned 23 s, fresh 53 s after the restart | 70 | Target Continue <=15 s (flowlive WIP) |
| A5 | Join any time / late joiner | Yes | Yes, with catch-up of progress + opening skip | 80 | party_catchup |
| A6 | Leave cleanly | Separation Mist leaves; if the host uses it the session disbands *(verify: weak source)* | Leave works (0.4 s) | 75 | Spurious "Session lost" notice (flowlive WIP); host "End party" with 2 guests untested |
| A7 | Player count | 6 total (host + 5) | 3 live-verified; 4 coded (party_fourp), not live (needs 4 slots) | 50 | 5-6 not planned yet |
| A8 | Settings in game | ersc_settings.ini: [GAMEPLAY] allow_invaders, death_debuffs, allow_summons, overhead_player_display; [SCALING]; [PASSWORD]; [SAVE]; [LANGUAGE] | All settings in the game's own System menu, Party pages | 90 | bbport_game_menu |

## B. World & travel

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| B1 | No tether / roam anywhere | Players roam freely, anywhere | Confinement walls opened; players can stand in different map blocks (stale-hit crash fixed) | 75 | travel.md §7, 146 m split held 2+ min. Real stick walk-away not tested |
| B2 | Fog / boss gates | Everyone can enter | Fog gates by pad verified | 80 | b2_seamless.md §6.8 |
| B3 | Fast travel | Party travels together (vote) *(verify)* | Any member's lamp / headstone / mark becomes a party move with one loading screen (B2) | 85 | B2 default; 5 lamp warps in a row |
| B4 | Loading screens | One load, no rejoin | One load, guests stay clients (B1 fallback after 45 s) | 85 | b2_seamless.md |
| B5 | Independent travel (split party travels apart) | Each player can be anywhere *(verify)* | Not supported: travel always moves the whole party | 20 | Design choice; revisit after C2 |
| B6 | Scripted transitions, Hunter's Mark, headstones | n/a | All keep the session | 85 | edgetravel 6 cases |

## C. Death & respawn

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| C1 | Guest dies alone | Session kept; death gives a Rot Essence debuff (death_debuffs). In a boss fight the dead player spectates until the party wipes or someone rests at a grace; respawn point outside fights *(verify)* | Respawns alone at a lit lamp in the party's map, keeps echoes, no bloodstain; host plays on | 80 | b2_seamless.md §6.10-6.11 |
| C2 | Host dies alone | Session kept, others play on *(verify)* | Session kept, but the WHOLE party is moved to the host's lamp (one load); guests keep HP and items | 50 | Next: host respawn without a map reload (custom revive + warp) |
| C3 | Party wipe | All respawn, session kept | Same; verified | 90 | §6.8 r8-r15 |
| C4 | Death penalty | `death_debuffs=1`: stacking Rot Essence debuff on each death, cured only by resting at a grace (later versions: max 5 stacks, no stacks from a boss wipe) | Vanilla echo loss for the host; guest keeps echoes; no debuff | 40 | Decide: bloodstain for the guest? configurable debuff? |
| C5 | Spectate while dead | Yes: during a boss fight until a wipe or a grace rest | None | 0 | |
| C6 | Rejoin after a crash / redirect | Rejoin by item | ~4.5 s ring to client after the world is up; crash rejoin ~30 s | 80 | §6.11 |

## D. Progress: anyone can progress

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| D1 | Boss kills count for everyone | Yes | Yes (K10); session kept after the kill | 85 | |
| D2 | World state shared (doors, shortcuts, lamps) | Host's world; progress carries over | Host world flags mirrored to guests live (~0.3 s); guest's own save gets C2 progress | 80 | event_flags.md §12. Visual door check pending |
| D3 | Guest actions change the host's world | Yes *(verify)* | Lamp lighting via host only. Guest levers / doors / shortcuts not routed | 30 | Next: generalise the lamp_lit request to levers/doors |
| D4 | Items & pickups | Random drops instanced per player; persistent loot (bosses, scarabs) for everyone in the area; one-time items not re-granted if already owned | Summoned awards, item-get dialog, blood gems for guests | 75 | C3 |
| D5 | Quests, NPCs, story | Progress is saved by the host's progression; quest progression "can be erratic" (FAQ advises solo + backups) | Story choices (C4), endings for summoned guests | 65 | Full NPC quest lines untested; campaign soak WIP |
| D6 | Full campaign start to credits | Playable | Not yet soaked end to end | 30 | campaign_soak (edgetravel WIP) |
| D7 | Enemy scaling | Per-player scaling of enemy and boss health / damage / posture ([SCALING] keys) | Vanilla co-op scaling only, not measured | 20 | Check; add Party setting |

## E. Services & UI

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| E1 | Rest / level / shop for guests | Everyone uses graces | Doll level-up, shops, workbench, storage; lamps + headstones (on by default); rest heals the guest | 85 | guest_services.md |
| E2 | Party HUD / names | overhead_player_display: normal / none / ping / soul level / death count | Party HUD, toasts | 70 | No overhead names |
| E3 | Map markers | Party shown on the map | n/a (BB has no map) | — | |
| E4 | Item / summon messages fast | n/a | Fast multiplayer messages, no bell/sign waits | 90 | fast join patches |

## F. Network & robustness

| # | Feature | ERSC | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| F1 | Real internet play (latency/loss) | Works over Steam | Only loopback tested | 20 | Net simulator + reliable party events (overlay WIP) |
| F2 | NAT traversal | Steam relay | Direct IP; UPnP / port forward not done | 20 | network_robustness.md (WIP) |
| F3 | Security | n/a | Hardening + fuzzing of party events | 80 | party-security-test |
| F4 | Invasions | allow_invaders (on or off; sources disagree on the default) | None (serverless) | — | Not planned |
| F5 | Watchdog / desync recovery | n/a | Watchdog, B1 fallback | 70 | |

## G. Bloodborne-specific

| # | Feature | ERSC analogue | bbport now | % | Evidence / next |
|---|---|---|---|---|---|
| G1 | Chalice dungeons in party | Catacombs work in co-op | Guest summoned into the host's dungeon live; no full clear; two one-off crashes | 45 | chalice full clear (bossk10 WIP) |
| G2 | Insight, Messengers' bath, Insight items | — | Untested for guests | 10 | |
| G3 | Blood Moon / world phase changes | — | Untested in party (part of the soak) | 25 | |

## Change log

- 2026-10-11: table created from the state of the integration branch at 580fbd3.
- 2026-10-11: ERSC column checked against ersc-docs.github.io (settings + FAQ).
