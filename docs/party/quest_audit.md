# Quest audit: the whole campaign against the party sync (2026-10-14)

Static audit of every co-op relevant event of Bloodborne 1.09 (EMEVD event scripts, ItemLotParam,
ObjActParam, NpcParam, talk ESDs, MSBs) against what the party code does today
(`windows-upstream-0.5` after 0.6.1 packaging). Goal: find before the next Internet session
(the host and the guest, continuing from Old Yharnam) the key items, doors, warps, fog walls and
NPC steps that can break co-op. Nothing here was run live (except P1 and P7, marked live); "verified" means checked in the data
and the code, not on screen.

How it was made (repeatable, game data read-only from an agent game copy):

* `python -I tools/party/flag_tool.py emevd GAME/event --all-ops --json OUT` (every event, slot,
  flag write, item lot, cutscene, map move), plus a scratch pass that also records item checks
  `3[4]`/`3[16]`, item removal `2003[24]`, chr warps `2004[3/40/41/42]` and insight checks `3[26]`.
* ItemLotParam rows whose items are goods 4000-4999 / chalices (key items), joined with the
  awarding events and `party_items.inc` (ledger / lot flag tables) and goods names from
  `msg/engus/item.msgbnd.dcx`.
* ObjActParam rows with `spQualifiedType = 1` (doors that need a key item).
* MSB enemy parts with a talk id (talk NPCs) against NpcParam byte 0x145 (ghost bit) and
  `party_npcghost.h`.
* Talk ESDs scanned for the NPC gift trigger flags 9042-9077 (common event 9040).
* Code read: `party_flags.inc` categories and the C2 policy (`party_progress.cpp`), the world
  mirror, C3 items (`party_items.cpp`), world actions (`party_worldact.cpp`), split travel
  (`party_split.cpp`), travel capture/replay (`party_travel.cpp`), host death (`party_b2.cpp`),
  story dedupe (`party_story.cpp`).

---------------------------------------------------------------------------------------------

## Next session checklist (Old Yharnam -> Blood-starved Beast -> Cathedral Ward -> Hemwick / Forbidden Woods -> Byrgenwerth)

The ten things most likely to go wrong in the next ~5 hours, and what to do in game.

1. **Snatchers (kidnappers) appear as soon as the Blood-starved Beast dies** (m24_00 12400791 /
   m27 1270501: on while flag 9453 "Blood-starved Beast killed" is set and the Blood Moon 9802 is
   not), in Cathedral Ward and the Forbidden Woods. Only the **host** can be kidnapped
   (12400780 / 12700500 need chr type 0); a guest killed by a Snatcher just dies (party death).
   The host's grab-death sets 9420, common 9421 moves the host's respawn point to the Hypogean Gaol
   (ReturnPoint 2802959, Yahar'gul) and the host's death becomes the party's respawn load; the
   guests replay it as a lamp warp to the host's last lamp record, which is then the Gaol
   (**P7 done**: `2003[23]` is the dispatcher case 0x17C10A5, it writes GSM +0x1528 = {row +4, row +8}
   of the ReturnPointParam row; live: host `respawn load for the whole party at lamp 2802959`, guest
   `replay ... host_death ... last lamp 0x2ac50f via lamp warp`, one loading screen, guest placed
   0.5 m beside the host in the cell).
   *In game:* everyone wakes up in the Hypogean Gaol (a cell, Yahar'gul) with one loading screen;
   the host sees the waking scene, the guest's loading screen waits for it ("Waiting: the host is
   watching a cutscene"). Avoid the grab if you do not want to go to Yahar'gul yet: kill Snatchers
   from range or let the guest tank them.
   *Fixed here:* 9420 is no longer copied into the guest's own save (it would have sent the
   guest's next solo death to the Gaol). The guest's own save gets 9421 / 9423 (key_event: "kidnap
   done") and, once it goes home and rings again, the Gaol as its own last lamp (the bell's gather
   lamp warp to the host's lamp) - the same state as a solo kidnap, never a pending one.
   *Open (minor):* the host's +1 Insight at the end of 9422 (SpEffect 4680, host only) is not
   shared with the guests.
2. **Blood-starved Beast reward (Pthumeru Chalice)**: lot 80000000, flag 5000 (global) -> shared
   with every member through C3; the guest's item box waits for the boss banner to end. No intro
   cutscene, so the guest may go through the fog first (B2). *If the chalice is missing on the
   guest:* Leave + Join party (the rejoin resends the full item list); check the guest's log for
   `lot 80000000`.
3. **NPC gifts when the guest is the one who talks** (Djura's Powder Keg Hunter Badge in Old
   Yharnam, Eileen's badges, Alfred, Gilbert's Flamesprayer, the Oedon Chapel Dweller, the old
   woman's / old man's gifts, Patches). **P1 done (live):** the talk script's trigger flag
   (9042-9077) set on the guest goes to the host as a world action; the host's common event 9040
   awards the lot and C3 gives it to every member once. Live (Eileen, Cathedral Ward, test save):
   before the fix the guest heard "Here, to welcome the new hunter", got only the gesture, no Bold
   Hunter's Marks, and Eileen's state 72400520 moved on in the host's world (gift lost for
   everyone); with the fix guest log `NPC gift trigger 9074 set by its talk: to the host`, host
   `award lot 35000`, guest `gave ... lot 35000 ... goods 1400 x4 (held 2 -> 6)`, both saves 1400 x6,
   the host's own talk afterwards gave nothing more. *In game:* either player may talk.
4. **Vicar Amelia: the first fight starts with the host.** Her intro (12401802, remo 24000060)
   runs only on the host (chr type 0), so the guest-first fog does not apply. *In game:* the host
   goes through the fog first; the guest follows. Reward lot 50000001 (goods 4001) is a ledger lot
   -> shared.
5. **Amelia's skull (evening -> night)**: 12401803 runs only on the host. *In game:* the **host**
   examines the skull at the altar; the guest sees the scene as a live mirror and its time of day
   is caught up. If the guest's world stays evening, it changes at its next summon (time-of-day
   catch-up).
6. **Hunter Chief Emblem** (Cathedral Ward corpse, lot 2400450) opens the plaza gate (12400760,
   gatekeeper; flag 12400160). Map treasure used to be per player. *Fixed here:* when the host
   picks it up, every member gets it (same for the Rune Workshop Tool in Hemwick and the Lecture
   Theatre Key in Byrgenwerth). The gate opened by anyone stays open for everyone.
7. **Scripted area changes now ask "Travel with the party?"** Every EMEVD `2003[49]` warp goes
   through the lamp warp hook, so the Hemwick carriage to Cainhurst, the Rom -> Blood Moon warp to
   Yahar'gul, the Lecture Building doors, the Amygdala grab and the DLC grab all open the travel
   question on the player who triggered them (after the cutscene). *In game:* answer **YES**. A NO
   leaves the others where they were; recover with the bell or a party lamp travel. This path was
   never run live after split travel landed (campaign soak row 7b passed before it).
8. **One-off host-only story steps**: the Blood Moon (Rom dead + host near Queen Yharnam,
   13201803), Willem's memory (5), first fights with an intro (Amelia, One Reborn, Wet Nurse,
   Micolash, Logarius), the Yahar'gul altar warp to the Lecture Building after One Reborn
   (12800430, `End if Client`). *In game:* the host does them; guests wait or watch.
9. **Lifts and two-state gates** (Forbidden Woods 12700131/132 lift and 12700171/172 gate,
   Hemwick 12200122/123 lift, Cathedral Ward 12400147/148 and 12400824/825 lifts): the guest sees
   the host's lift position (world mirror) and its own lever kicks go to the host. *If a lift
   looks stuck on one screen:* the other player rides it once or pulls the lever; a rest fixes
   everything.
10. **Insight differs per player**: the Yahar'gul Amygdala (12800401, Insight >= 40 or Blood
    Moon), Central Yharnam's big Amygdala (12410815, Insight >= 20), the Witch / Cathedral Ward
    checks (host only) are decided per game. Two players with very different Insight may see
    different monsters. *In game:* nothing to fix; mention it if one player is hit by something
    the other cannot see.

Also keep in mind: the guest should pick up its own copies of ordinary treasure (instanced, D4);
boss rewards, key items from bosses and NPC event awards arrive by themselves.

---------------------------------------------------------------------------------------------

## How the sync handles each kind of event (summary of the code)

| Kind | Host -> guest | Guest -> host | Code |
|---|---|---|---|
| Boss defeated (1AAB1800, 9452-9479) | world mirror (host's world live) + C2 set-only into the guest's own save; a boss of the map the guest stands in is held back in mode 0 | no (only the host's kill counts) | party_progress |
| Boss fight / fog state (T1 zone 4, `boss_area`) | not mirrored (vanilla snapshot only at join) | B2 fog report (`world_action fog`) | party_worldact |
| Doors, ladders, shortcuts (`shortcut_door`), area objects (`world_state`) | mirror + C2 set-only (two-state lifts: `State`) | world action set/clear (lifts: the ObjAct kick only) | party_worldact |
| Lamps (7AAB02xx, 1AAB78x0) | mirror + C2 | lit through the host | party_progress, guest services |
| Key events (9400-9439 minus 9420, KEY_KW events) | mirror + C2 set-only | world action, set only | |
| Cutscenes | live mirror on the guest (C4) + story dedupe; a guest's own scene goes up (`story_up`) | yes | party_story |
| Time of day 9800-9802 | only through the cutscene path and the summon catch-up, upward only | no | party_catchup |
| NPC quest 1000-1999, 9360-9399, 9480-9499, 9700-9799, 7AAB0nnn | Follow (set and clear), whole 20-flag NPC blocks | world action, set and clear | party_progress, party_worldact |
| Item pickups 5AABZnnn (map treasure) | per player (instanced) except `SharedKeyTreasureLot` (new) | the guest's pickup goes to its own save only | party_items, party_worldact |
| Global item flags 5000-5299 / 500000nn, boss and event awards (`2003[4]`) | C3 replay (flag or ledger 60009000+) | gift_up only for hostOnly 0 awards with a flag | party_items |
| Scripted warps `2003[49]` / `2003[14]` | split question (Ask), YES = party travel | a guest's warp becomes a lamp request | party_split, party_travel |
| Host death | party respawn load at the host's last lamp record | guests replay as a lamp warp | party_b2, party_travel |

---------------------------------------------------------------------------------------------

## Fixes in this change (data / tables, unit-tested)

| # | What | Before | After | Where |
|---|---|---|---|---|
| F1 | Snatcher kidnap trigger 9420 | `key_event`: host -> guest set-only. A host kidnap (or any 9420 the C2 scan caught) wrote 9420 into the guest's own save; the guest's next own-world load ran common 9421 (it ends only for clients), set its respawn point to the Hypogean Gaol and the guest's next solo death woke it in Yahar'gul | `never_sync` (override row); 9421-9439 stay `key_event` | `tools/party/flag_tool.py` OVERRIDE_ROWS, `party_flags.inc` (regenerated), tests/test_party_progress.cpp, tests/test_party_worldact.cpp |
| F2 | Progression keys and workshop tools found as map treasure | instanced: only the player who walked to the corpse got it; a guest without the emblem / key / tool was locked out in its own world (and could not open the plaza gate in the host's world either) | `SharedKeyTreasureLot`: Hunter Chief Emblem 2400450, Upper Cathedral Key 2800290, Iron Door Key 2600550 / 2600610, Lecture Theatre Key 3200720, Underground Cell Key 3500800, Rune Workshop Tool 2200360, Blood Gem Workshop Tool 2411000: the host's pickup is replayed to every member (C3, also in the rejoin full list) | `party_items.{h,cpp}` `InstancedTreasureFlag`, tests/test_party_items.cpp |
| F3 | Eye of a Blood-drunk Hunter (lot 10040, flag 50000100, DLC entry) | denied as a per-player Messenger gift, but its event 12101028 needs chr type 0, so a guest who lives in the host's Dream never got it | replayed from the host like any key item | `party_items.cpp` `ItemLotDenied`, tests |

Badges (Saw, Radiant Sword, Cosmic Eye Watcher, Old Hunter) and messenger cosmetics stay per
player: they only unlock shop stock or looks.

---------------------------------------------------------------------------------------------

## Per area

Columns: **ids** = event / flag / lot; **host** = what the host experiences; **guest** = what a
guest summoned in the host's world experiences under the current sync; **risk** = blocker /
major / minor / ok; **fix** = done here (F#), proposal (P#, list at the end) or none.

### Old Yharnam (m23_00) - current position

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Lamps | Old Yharnam 2302950, Church of the Good Chalice 2302951, Graveyard of the Darkbeast 2302952 (objects 12307800/820/840) | lights | lamps via the host, mirror + C2 | ok | |
| 12 ladders | 12301000-12301011 (2009[0]) | kicks down | mirrored; own-save set-only | ok | |
| Djura (tower) | talk t230323, NpcParam 6300 (solid); NPC state block 1xxx; gift trigger 9071 -> lot 33000 Powder Keg Hunter Badge + Bold Hunter's Mark (flag 50001700) | talk, gift through common 9040 | can talk (6300 has no ghost bit); its 9040 instance ended at load, so its view says "gift given"; its talk's trigger 9071 now goes to the host (P1) | ok (P1 fixed; same path as Eileen, live) | either talks (checklist 3); P1 |
| "Beast guardian" talk suppression | 12300750 / 12300751 (world_state) | | mirrored | ok | |
| Blood-starved Beast | defeat 12301800, host entry 12301802 (no remo), guest entry 12304811, late guest 12301803; sets 2300 (area gate, never_sync), 9453 | fight | B2 guest fog first allowed (no intro) | ok | |
| Blood-starved Beast reward | lot 80000000 Pthumeru Chalice, flag 5000 | gets it | C3 replay (flag 5000), popup after the banner | ok | checklist 2 |
| 9453 side effects | Snatchers (12400791, 1270501), Hunter's Dream / Messenger changes | | C2 sets 9453 in the own save | ok | checklist 1 |
| Darkbeast Paarl | defeat 12301700 (2003[12]), host entry 12301702 (no remo); reward lots 50800000 Spark Hunter Badge (ledger 38), 50800005 | fight | guest fog first allowed; ledger replay | ok | |
| NPC summons (Alfred, Yamamura, Yahar'gul hunter) | 12304400-12304432, need the Old Hunter Bell | signs only in single player | none | minor | none (vanilla) |

### Central Yharnam / Iosefka's Clinic / Great Bridge (m24_01) - done, kept for reference

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Oedon Tomb Key | lot 31000, ledger 25 (Gascoigne 12411800) | boss award | C3 + re-give when held 0 (playtest #16 fix) | ok | |
| Oedon Tomb doors | ObjAct 2410001 / 2410080 need goods 4000 | opens | can open with its own key; door state mirrored | ok | |
| Cainhurst Summons letter | 12410510 (clinic), lot 2410990 flag 52410990, `2003[4]` | award | captured award -> shared | ok | |
| Blood Gem Workshop Tool | lot 2411000 (treasure) | picks up | was per player | minor | F2 |
| Fake Iosefka gifts | t241314 -> 9047-9053 (common 9040 slots 7-13, ledger lots) | | same as Djura | ok (P1 fixed, live with Eileen) | P1 |
| Gilbert (window) | t241319 -> 9066 Flamesprayer (lot 29000, ledger 23) | | same as Djura | ok (P1 fixed, live with Eileen) | P1 |
| Gascoigne's daughter | t241320 -> 9067 Tiny Music Box (lot 30000, ledger 24); Red Messenger Ribbon / brooch (12410713, lots 2410910/2410920) | | window talk works (D8) | ok (P1 fixed, live with Eileen) | P1 |
| Central Yharnam lift | 12410321-12410325, state 12410350/351 (`State`) | | mirror; world action refused (lift kick only) | ok | |
| Big Amygdala on the bridge | 12410815 (Insight >= 20, local) | | per player | minor | checklist 10 |
| Moon-presence / Arianna's child (night 3) | 12410833/834 | | npc_quest Follow | ok | |

### Cathedral Ward, Oedon Chapel, Grand Cathedral (m24_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Day -> evening on entering | 12400750 (ObjAct 7030 on door 2401210), remo 24000020 with warp 2402200 and tod 1 | done in playtest 1 | done | ok | |
| Hunter Chief Emblem | lot 2400450, flag 52400450 (treasure) | picks up | was per player | major | F2 |
| Plaza gate (gatekeeper) | 12400760: goods 4011 held by the local player + action 2400030 at 2401220; sets 12400160 (world_state); clears area gates 2400/2401/2405/2406 | opens | opens with its own emblem (now shared); a host-opened gate is mirrored and goes into the own save | ok after F2 | |
| Church lifts / trick doors | 12400147/148 (state 12400150/151), 12400824/825 (12400827/828), trick doors 12400155/156 (12400157), 12400125/126 (12400177/178), stair door 12400174/175 | rides | mirrored; doors that close again stay open in the own save (set-only) | minor | none |
| Vicar Amelia | defeat 12401800 (sets 2400-2402 never_sync), host entry 12401802 remo 24000060 (chr type 0), 9455 | intro + fight | intro only as the live mirror; fog: host first | major (wall until the host enters) | checklist 4; P5 |
| Amelia reward | lot 50000001 goods 4001 (ledger 35); ObjAct 2400080 needs goods 4001 | gets it | ledger replay | ok | |
| Amelia's skull -> night | 12401803 (host only), remo 24000030 tod 2 | plays, world -> night | live mirror; time-of-day catch-up into the own save (upward) | minor | checklist 5 |
| Snatchers | spawn 12400791 / 12400797 (9453 and not 9802); kidnap 12400780 (chr type 0) sets 9420 | kidnapped -> Gaol | dies normally; follows the host's respawn (live, P7) | ok | F1, checklist 1 |
| Insight checks | 12404000 (host only): Insight >= 15 -> 12404002, >= 40 -> 12404001, >= 50 -> 12404003 (Cathedral Ward variants, DLC Amygdala) | | zone 4 flags: the host's values via the vanilla join snapshot | minor | |
| Oedon Chapel NPCs | Dweller 113010 (t240312 -> gift 9045 Pebble), lonely old woman 6090 (t240316 -> 9054-9057 sedatives), old man 6080 (t240317/t240338 -> 9059-9064 pellets), Arianna 6110-6113 (Blood of Arianna: common 9100, repeatable, denied), Adella (9100, denied), Alfred 6151/6155 (t240333/t240343 -> 9072/9073), Eileen 6161 (t240325/t240341/t240342 -> 9074/9075 Crow Hunter Badge) | talk, gifts | solid since playtest 1; gifts as Djura; Blood of Arianna / Adella never for a guest | ok (P1 fixed) / minor (9100: P2) | P1, P2 |
| Beast beggar (suspicious beggar) | NpcParam 504020 (ghost bit kept as an enemy row), t240217 | talk | ghost on the guest: cannot talk | minor | P3 |
| NPC "scared" flag | 9432 (key_event; cleared at every m24_00 load by ev 50) | | harmless | ok | |
| Upper Cathedral Ward gate | ObjAct 2400100 needs Upper Cathedral Key (Yahar'gul treasure 2800290) | | key now shared (F2) | ok after F2 | |
| DLC grab | 12400765 shows Amygdala 2400899 at Blood Moon or 12404001; 12405263 needs goods 4311 on the local player; host: 12401000 + `2003[49] 3402959` | grab -> travel question | grab cutscene only (chr type != 0 ends) and needs its own Eye (F3) | minor | checklist 7 |

### Hemwick Charnel Lane (m22_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Lamps | 2202950, 2202951 | | via host | ok | |
| Lift | 12200122/123 (state 12200125/126) | | mirrored | minor | |
| Rune Workshop Tool | lot 2200360 (treasure) | picks up | was per player -> no Memory Altar for the guest | major | F2 |
| Witch of Hemwick (Eye Collector) | defeat 12201800 (2200 never_sync, 9452), host entry 12201802 (no remo), insight checks 12204844 / 12204010 host only; lot 21002950 (ledger 31) | fight | guest fog first; ledger replay | ok | |
| Cainhurst carriage | 12200130 (appears: local player holds goods 4003 + 12201800 + in region 2202410), 12200131 (action, remo 22000040, `2003[49] 2502959`) | travel question | with its own summons (shared) it can call the carriage too -> its question -> party request | minor | checklist 7 |
| Hostile crowd woman back throw | 12205080 | | | ok | |

### Forbidden Woods (m27_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Lamps | 2702950, 2702951 | | via host | ok | |
| Lifts / gate | lift 12700130-132 (12700134/135), lift 12700140-142 (12700144/145), gate 12700170-172 + 12705490 (12700173/174) | | mirrored, State | minor | |
| Snatchers | 1270501 (spawn), 12700500 (kidnap, chr type 0) | | | major | F1 |
| Shadows of Yharnam | defeat 12701800 (2700/2701 never_sync, 9463), host entry 12701802 (no remo); lots 2700990 (flag 52700950), 2700995 | fight | guest fog first; captured award (map flag) -> shared | ok | |
| Valtr / League (t270503, 6500), beggar 504030 (t270217, ghost), old man 6100 (t270317 -> 9058 Pungent Blood Cocktail) | | | gifts as Djura; beggar ghost | minor | P1, P3 |
| NPC summons (Henryk, executioner) | 12704400-12704431 | | | minor | none |

### Byrgenwerth, Lecture Building, Moonside Lake (m32_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Lamps | 3202950-3202953 (+ script points 3202956-3202959) | | via host | ok | |
| Lecture Theatre Key | lot 3200720 (treasure); ObjAct 3200030 | picks up | was per player | major | F2 |
| Lunarium Key | 13200400 award lot 3200810 (flag 53200810); ObjAct 3200040 | award | captured -> shared | ok | |
| Willem | 513000 (ghost bit kept), t320310; 13200121 points at the moon | | ghost on the guest | minor | P3 |
| Rom | defeat 13201800 (3200 never_sync, 9465), lot 51001900 (ledger 40) | fight (no intro) | guest fog first | ok | |
| Blood Moon | 13201803 (host only: Rom dead + near Queen Yharnam 3200801), remo 32000000 tod 3, sets 70002802, `2003[49] 2802958` | cutscene -> travel question | live mirror; time-of-day catch-up; follows the party travel | major (question path untested live) | checklist 7/8 |
| Lecture Building doors | 13200310 (ObjAct 13200124 -> `2003[49] 2602959` Nightmare of Mensis), 13200311 (ObjAct 13200123 -> `2003[49] 3302959` Nightmare Frontier) | question | its own question (both may be asked) | minor | P4 |
| Lecture Building arrival via Amygdala | 13200950 (clears 12800434) | | | ok | |

### Yahar'gul, Unseen Village (m28_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Hypogean Gaol (kidnap) | common 9421 (respawn 2802959), 9422 (remo 28000010 in m28, sets 9423, SpEffect 4680; `End if Client`) | wakes in a cell | follows the respawn with one loading screen, beside the host (live, P7); its loading screen holds through the host's waking scene; misses the host's +1 Insight of 9422 | ok / minor (Insight) | F1, checklist 1 |
| First-sacrifice multiplayer block | 12800160: SpEffects 9120/9121 while 9802 is off | | cutscenes_endings.md 5.2: unknown effect on summons in m28 | major (untested) | P6 |
| Time of day | 12800400 (sets 2800 never_sync, 70002802), gates 12800402/12800403 by 9802 | | mirrored | ok | |
| Upper Cathedral Key | lot 2800290 (treasure) | picks up | was per player | major | F2 |
| One Reborn | defeat 12801800 (2800, 9464), host entry 12801802 remo 28000000; lot 50700000 (ledger 37) | intro + fight | host first | major | checklist 8, P5 |
| Altar warp to the Lecture Building | 12800430 (`End if Client`, action 2800020 at 2801500, `2003[49] 3202959`) | question | cannot use it | minor | checklist 8 |
| Amygdala grab (Tonsil Stone) | 12800401 (visible at Insight >= 40 or Blood Moon, local), 12800431 (event message 10 of 2800745 + goods 4310 on the local player, remo 28000040/28001040, `2003[49] 3202958`; **no client guard**) | question | a guest holding the Tonsil Stone runs its own copy too (its own question) | minor | P4 |
| Tonsil Stone | lot 39000 (common 9040 slot 36, ledger 28, done 9076); its trigger 9076 is in no talk ESD (set by another path; Patches' state 9782 checks the stone) | award | ledger replay | ok (who triggers it: unverified) | |
| Patches | t280322 -> 9069 (Madman's Knowledge) | | gifts as Djura (P1 fixed) | minor | P1 |
| NPC summons | 12804400-12804431 | | | minor | |

### Upper Cathedral Ward, Lumenwood Garden, Altar of Despair (m24_02)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Orphanage Key | 12420700 (brain eater drop) lot 2420900 flag 52420900, `2003[4]` | award | captured -> shared | ok | |
| Orphanage door | ObjAct 2420020 needs goods 4006 | | own key (shared) | ok | |
| Lift to Ebrietas | 12420150-12420156 (State 12420154/155) | | mirrored | minor | |
| Celestial Emissary | defeat 12421700 (2420), entry 12421702 (no remo); lots 25700000 / 25700005 (ledger 33/34) | | guest fog first | ok | |
| Ebrietas | defeat 12421800 (2421, 9459), entry 12421802 (no remo); lot 80000300 Great Isz Chalice flag 5009 | | shared | ok | |
| Queen Annalise revival | 12420500 (removes goods 4305 Queenly Flesh, remo 24020000) | | | minor | |
| Insight check | 12425290 (host only, >= 10) | | | ok | |
| Cosmic Eye Watcher Badge | lots 2420270 / 2420280 (treasure, per player) | | per player | ok | |

### Forsaken Cainhurst Castle (m25_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Arrival | carriage `2003[49] 2502959` (from Hemwick) | party travel | follows | minor | checklist 7 |
| Lift | 12500074 (12500076/077) | | | minor | |
| Martyr Logarius | defeat 12501800 (2500, 9460), host entry 12501802 remo 25000020 | intro + fight | host first | major | P5 |
| Unopened Summons | 12500600 lot 2500910 flag 52500910 (award) | | shared | ok | |
| Queenly Flesh | 12500020, lot 2500920 | | | ok | |
| Annalise / Yurie / Alfred | 6040 (t250307 -> 9042 lot 17000 Cainhurst Badge), 6150 (t250324) | | solid; gifts as Djura | ok (P1 fixed, live with Eileen) | P1 |
| Church marks | 12500206 / 12500220 (world_state toggles) | | | minor | |

### Nightmare Frontier (m33_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Arrival | Lecture Building door 13200311 (`2003[49] 3302959`) | question | | minor | |
| Patches' push | 13300200 (remo 33000000/33001000 + warp 3302171 in the same map) | | local player | minor | |
| Lift | 13300110-13300113 (13300115/116) | | | minor | |
| Amygdala | defeat 13301800 (3300, 9466), entry 13301802 (no remo); lot 80000200 Ailing Loran Chalice flag 5006 | | shared | ok | |

### Nightmare of Mensis (m26_00)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Arrival | Lecture Building door 13200310 (`2003[49] 2602959`) | question | | minor | |
| Iron Door Key | lots 2600550 / 2600610 (treasure); ObjAct 2600020/2600021 | | was per player | major | F2 |
| Lifts | 12601320/330/340/352 (12601250-12601256) | | | minor | |
| Micolash | defeat 12601850 (2600, 9461; clears 1080-1099), host entry 12601852 remo 26000060; post scene 12601854 host only; lot 21000 Mensis Cage (ledger 3) | intro + fight | host first | major | P5 |
| Mergo's Wet Nurse | defeat 12601800 (2601, 9462 final night), entry 12601802 remo 26000010, spawn needs the host in region 2602805; lot 55100000 One Third of Umbilical Cord flag 50000305 (global -> shared) | | host first | major | P5 |
| 9462 "final night" | Hunter's Dream burns, Gehrman's offer | | C2 | ok | |

### Hunter's Dream (m21_00, m21_01)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Doll level-up | 12100112-12100118, 72100100-72100113 never_sync (playtest 1) | | per player | ok | |
| Messenger gifts | Old Hunter Bell 10050 (own grant), Beckoning / Small Resonant Bell 10010 / 10000 | | own grant | ok | |
| Eye of a Blood-drunk Hunter | 12101028 (chr type 0, night 9801, DLC flag), lot 10040 flag 50000100 | gets it | never for a guest | minor | F3 |
| Badge shops / workshop tools | 12101000 (badges held), 12100450 (tools held) | | own inventory | ok | F2 for the tools |
| Tear Stone | 12100123 lot 14000 (ledger 0) | | ledger | ok | |
| Abandoned Old Workshop | 12110300 Small Hair Ornament, 12110301 umbilical cord (lot 2110810, flag 52110810, award) | | shared | ok | |
| Gehrman / Moon Presence / endings | cutscenes_endings.md 3.3 / 4.4; 72100130/131, 21-23 never_sync | | C4 replay | ok (soaked) | |

### DLC: Hunter's Nightmare, Research Hall, Clocktower, Fishing Hamlet (m34, m35, m36)

| Event | ids | Host | Guest | Risk | Fix |
|---|---|---|---|---|---|
| Entry | 12405263 grab (host warp 3402959); arrival 13401000; multiplayer wall 13400010 until Ludwig | question | follows the party; needs the DLC (6899) | minor | F3 |
| Ludwig / Laurence | 13401800 / 13401850 (personal flags 6673/6674, exceptions in ItemLotDenied); Laurence needs goods 4014 Laurence's Skull (13404861 / 13401851) | | | minor | |
| Research Hall keys | Underground Cell Key 3500800 (treasure, F2), Inner Chamber Key 43220 (Simon, flag 50002350 global), Balcony Key 43010 / 43030 (flag 50002250 global), Astral Clocktower Key 3501850 (award), Celestial Dial 3501800 (award), Eye Pendant 3401810 (flag 9470) | | shared | ok after F2 | |
| Clocktower altar | 13501105 (goods 4017, phantom-aware), 13501140 | | | minor | |
| Research Hall talk NPCs | NpcParam 402080, 402090, 402280, 402281, 402290, 402300 (talks 3505xx), Fishing Hamlet 405100 (t360507), 409000 (t340540), Ludwig's head 451100 (t340508) keep the ghost bit | | ghosts: no talk (Adeline, patients, Ludwig's head) | major (DLC) | P3 |

### Chalice dungeons

Out of scope here (chalice.md, bossk10): ritual chalices from bosses are global flags 5000-5053
(shared), dungeon flags are never_sync.

---------------------------------------------------------------------------------------------

## Proposals (not done here)

* **P1 NPC gifts triggered by a guest. DONE (kidnap agent, 2026-10-14, live).** Common event 9040
  slots 2-37 award the NPC gifts when the talk ESD sets the slot's own flag (9042-9077; each id is
  in its ESD exactly once, as the SetEventFlag argument: the gift branch is chosen by the NPC's own
  state flags, not by this one). On a client 9040 ends at load (chr type 0 only) and its slot flag
  reads 1 in the guest's overlay from then on (watch: `9074: visible 1, own save 0, host image 0`),
  so the guest's talk set nothing new, awarded nothing, and the NPC state (npc_quest) still moved
  on in the host's world. Fix: `party_worldact` observes this game's own SetEventFlag calls
  (`progress::AddLocalFlagSetObserver`); a gift trigger (`NpcGiftTrigger`) the guest's talk sets
  while it stands in the host's world goes up as a set-only world action
  (`WorldActionAllowed`), unless the host's image already has it; the host's 9040 awards the lot,
  C3 hands it to every member (ledger / lot flag), the guest's own save gets the trigger. Live:
  see checklist 3.
* **P2 Repeatable NPC gifts for guests** (9100 slots): `MessengerGiftLot`-style own grant.
* **P3 Remaining ghost NPCs**: the beast beggar 504020/504030, Willem 513000 and the DLC talk
  NPCs (402080-402300, 405100, 409000, 451100) still have the ghost bit. They are enemy-family
  rows, so clearing the bit also changes how their hostile uses look on clients: check each row's
  users in the MSBs and verify in the DLC before adding them to `party_npcghost.h`.
* **P4 Double travel questions** for scripted warps that run on both games (Lecture Building
  doors via the replicated ObjAct, the Tonsil Stone grab on a guest holding the stone): the host
  should drop a guest's lamp request for the same id while its own question or travel for that id
  is pending (party_split / party_guestsvc).
* **P5 First fights with an intro** (Amelia, One Reborn, Logarius, Micolash, Wet Nurse; DLC
  bosses): let a guest's fog report make the host play the intro and open the fight, or at least
  show "Waiting for the host: this fight starts with a scene" (playtest1_triage.md bug 8).
* **P6 Yahar'gul before the Blood Moon** (12800160 SpEffects 9120/9121, the Gaol): verify a
  summon / B2 travel into m28 with 9802 off before the players get kidnapped (only reachable by a
  kidnap before Rom).
* **P7 Kidnap respawn trace. DONE (kidnap agent, 2026-10-14, live).** The EMEVD dispatcher
  0x17C0420 switches on the 2003 instruction id (jump table 0x17C2C38); id 23 (`復活ポイント設定`,
  set respawn point) is the case at 0x17C10A5: row lookup 0x1F26B40, then `GSM +0x1528 =
  {row +4 | row +8 << 32}` (0x17C1145). (Id 20 writes +0x1530 the same way.) So the host's last
  lamp record is the Gaol before its death funnel, and the guests' host_death replay lands there.
  Live (2 instances, test save, host in Cathedral Ward, `host_flag=9420` then `host_die`):
  one loading screen for both, guest 0.5 m beside the host in the cell, no stuck or half state.
  A guest cannot be kidnapped in the host's world (12400780 / 12700500 end unless the local chr
  type is 0; a summoned guest is type 1 within 0.3 s of arriving).
* **P8 Scripted warp question**: consider skipping the travel question for scripted `2003[49]`
  warps that are story transitions (Blood Moon 2802958, DLC 3402959, carriage 2502959, Lecture
  Building 3202958 / 3202959 / 2602959 / 3302959) and always travel with the party, as the
  vanilla game moves only the host and expects phantoms to go home.
* **P9 One-way doors that close again** (12400157, 12400177, 12700173): C2 set-only leaves them
  open in the guest's own save; sync their state like the lifts if it matters.

## Regenerating

`python -I tools/party/flag_tool.py gen-inc GAME --out gpu/shim/party/party_flags.inc` (the 9420
override lives in `OVERRIDE_ROWS`); the key treasure list is `SharedKeyTreasureLot` in
`party_items.cpp`.
