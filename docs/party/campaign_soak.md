# Campaign soak: new game to end credits with a party (2 players)

Live soak of the whole campaign path with the in-game party flow, 2026-10-11 (edgetravel,
integration `windows-upstream-0.5` @ 25348ea .. 0bf258b). Two loopback instances
(`tools/mp/instances.py run --count 2 --party`), **fresh characters** for both (empty
`user\savedata_party`), and from then on the **same saves for every run**: each run starts from
the title with *Continue party game* (auto-continue), so every run after the first is also a
"Continue resumes the same world on both sides" check. No OS input: the director's test steps
(`BB_PARTY_DIRECTOR_TEST`, party_director.cpp) and the test aids of test_newgame.h.

Runs are short (the machine-wide game queue ends a run after 240 s when others wait), so the
soak is a chain of runs 1, 2, 3, 4, 4b, 5, 5b-5d, 6-6d over the same two saves.

Evidence is the `Party progress: test read (load mode N, own save / visible)` line both
instances log at every steady load (`BB_PARTY_PROGRESS_TEST_READ`): `own` is what the player's
**own save** holds, `visible` what its game sees now (the host's overlay while summoned).

## Checklist

| # | Milestone | How (test steps) | Session survives | Same map | Progress in the guest's own save | Crash-free | Result |
|---|---|---|---|---|---|---|---|
| 0 | Integration HEAD healthy | merge + build + all party-*-test + party-security-test | - | - | - | - | **pass** (18/18) |
| 1 | New party game, fresh characters, clinic -> Dream -> Central Yharnam | `BB_TEST_NEWGAME=1` both; host `BB_TEST_PROLOGUE_SKIP=1 WARP=dream`; guest catch-up; `host_warp=2412951` | yes | yes (after the host's warp) | campaign-start flags + weapons (catch-up) | yes | **pass after fix 1** |
| 2 | Cleric Beast | `host_warp=2412952`, `host_kill=2410800` | yes (K10 kept the party) | m24_01 | 12411700 = 1/1, Insight +3 (parity), item grant | yes | **pass** |
| 3 | Father Gascoigne | `host_warp=2412953` (Tomb of Oedon), `host_kill=2410810` | yes | m24_01 | 12411800 = 1/1 | yes | **pass** |
| 4 | Cathedral Ward | `host_warp=2402950` | yes | m24_00 | - | yes | **pass** |
| 5 | Vicar Amelia | `host_warp=2402951`, `host_kill=2400800` | yes | m24_00 | 12401800 = 1/1, grant | yes | **pass** (evening -> night skull 12401803 not triggered: an object action) |
| 6 | Forbidden Woods | `host_warp=2702950` | yes | m27 | - | yes | **pass** |
| 7 | Rom | `host_warp=3202951`, `host_kill=3200800` | yes | m32 | 13201800 = 1/1 | yes | **pass** |
| 7b | Blood Moon (Rom -> Queen Yharnam) | `host_walk` 4 m from Queen Yharnam (MSB 3200801 at (-510.9, -271.3, 370.4)) | yes | host's event warp to m28, guest followed (B2) | cutscene 32000000 on both (live mirror); time of day 3 written to the guest's own pool (9800..9802 0 -> 7) | yes | **partial**: the tod write did not survive into the next session (see open 2) |
| 8 | Nightmare Frontier | `host_warp=3302950` | yes | m33 | - | yes | **pass** |
| 9 | Micolash / Mergo's Wet Nurse | lamp 2602953, `host_walk` into the Wet Nurse arena (138.8, 1125.2, -37.9), `host_flag=12604800`, `host_kill=2600800`; Micolash by `host_flag=12601850` | yes | m26 | 12601850 (set by flag) = 1/1 on the guest | yes | **blocked (test tooling)**: no boss defeat (open 3) |
| 10 | Gehrman | `host_flag=72100131` (the refusal choice), `host_skipremo`, `host_kill=2100800` | yes (K10) | m21 | 12101800 boss defeat, Insight to the guest | yes | **pass**; refusal cutscene 21000040 on both (live mirror, 108 s) |
| 11 | Ending B (Honoring Wishes) + credits, guest gets them | `host_walk` to the Gehrman arena (MSB point 2102808 at (28.4, -9.2, 5.6), on hit parts 2103601-5) | until the ending (the guest leaves to play it in its own Dream, by design) | m21 | guest's own save: 12101800, 9180, 6604 / 6601 / 6603, **22**, NG cycle 0 -> 1 | yes | **pass**: host event 12100000 -> remo 21000020 (72 s) -> NG cycle 1 -> ending step (world down = staff roll); guest got `ending 2` at the same second, warped to its own Dream, same remo 72 s, flags, NG cycle 1, ending step |
| 13 | A fresh guest joins the advanced host late (run 7: host save from before the ending, guest `BB_TEST_NEWGAME`) | catch-up, gather, summon, `host_warp=2412952` | yes | yes | after the gather load (own world, m21): 12401800, 13201800, 12601850, 12101800 = 1; after the summon + travel to m24_01: 12411700, 12411800 = 1/1 (the current map's boss flags land at that map's load); **time of day 9800..9802 = 0/1, 13201803 = 0/1** | yes | **partial**: every boss caught up into the own save; the Blood Moon did not (open 2b) |
| 12 | Continue party game resumes the same world | every run 2..6d | yes | yes | yes | yes | **pass** (host back where it saved; guest re-summoned, 20-110 s after start) |

User design decisions (ERSC_PARITY.md "Design decisions"), per milestone:

| Decision | Result |
|---|---|
| A guest behind the host catches up fully in its own save (bosses, Blood Moon, lamps, shortcuts) | **partial**: bosses **pass** (rows 2, 3, 5, 7, 9 while summoned; row 13 for a fresh guest joining late: all six boss flags in its own save); campaign start **pass** (rows 1, 13); Blood Moon **fail** (row 7b: not kept; row 13: a late joiner's own time of day stays 0, open 2b); lamps / shortcuts not measured in this soak |
| NPC quest choices are shared (anyone's first choice counts) | **not covered**: no NPC quest step in this soak (the Gehrman refusal was set by the host only) |
| Cutscenes play for everyone | **pass**: Blood Moon 32000000 and Gehrman's refusal 21000040 played on the host and on the summoned guest (live mirror) |

## Fixes made during the soak

1. **A party started from two new games never summoned** (row 1). The guest connected while the
   host was still in its prologue; the late-joiner catch-up read "the host is in its prologue:
   nothing to catch up to" from the host's first flag snapshot and the guest waited in its first
   Dream for good (the prologue flags are not in the change stream). The host now re-sends its
   snapshot when 12410000 && 9401 turn on (party_progress_bridge.cpp). Live: catch-up, gather,
   summon 27 s after the host's prologue, then the host's warp to Central Yharnam with the guest
   following (B2, 14.7 s).
2. Test steps added (party_director.cpp): `%MAP` on any step (steady-world clock, so warps and
   kills chain without re-joins), `host_walk=chrENTITY`, `host_flag=ID` (a talk-menu choice),
   `host_skipremo` / `guest_skipremo` (the game's own cutscene skip request), `host_kill` logs
   whether the entity is in the character table.

## Open (not fixed here)

1. **Gather target for a fresh host** (row 1): the guest's gather warp used the host's "last lamp"
   2412959 (the record a fresh character has: m24_01) while the host stood in the Dream, so the
   guest joined the host's world in m24_01 and the two were split until the host's next travel.
   Better: gather to the host's current map (roster) when its last-lamp record is the default.
2. **Time of day written while summoned did not persist** (row 7b): the guest logged `own save
   9800..9802 0 -> 7 (pool)` 0.4 s before the run was ended; in the next session its own save read
   9800 = 0 (13201803 too). The write already requests a save (`RequestGameSave`, party_story),
   but GameSaveTick waits for 30 steady frames (and at most one save per 15 s), so a quit right
   after the cutscene loses it, and the story item is not replayed later. Fix idea: keep the item
   queued until a save went through, or re-derive the own time of day from the host's snapshot
   at each join.
2b. **Blood Moon is not part of the late-joiner catch-up** (row 13): the C2 snapshot brings boss
   flags into the own save, but the time of day (9800..9802, set by the host's event 13201803 with
   `2003[...]` value ops, not a boolean the change stream carries) and 13201803 stay 0 in a late
   guest's own save. Needed for the user decision "a guest behind catches up fully": copy the host's
   time-of-day value into the own pool at the catch-up / join (party_story already has the write
   for the live case).
3. **Mergo's Wet Nurse could not be killed by the test tooling** (row 9): ForceDead on 2600800 at
   the arena with the fight-start flag set gave no 12601800; the boss is spawned by its fight-start
   event (host enters the arena region), which a flag write does not run. Not a party bug; a real
   playthrough (or a region trigger aid) is needed.
4. **Gehrman's refusal cutscene played a second time on the guest** right after the live mirror
   ended (run 6b, `remo playing` again at +254 s): a queued replay of the same story item after the
   live mirror. Check the story queue's de-duplication.
5. Summons took longer late in the day (host hosting 85-108 s after start, guest joined 70 s
   later in run 6): machine load (10+ queued runs); not investigated.
