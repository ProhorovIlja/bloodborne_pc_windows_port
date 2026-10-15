# Test save fixtures (start mid-campaign)

Live party tests never start from a new game: every run Continues a test save (auto-continue) and
uses test aids to get to the moment it tests. The saves live **outside the repo** under
`E:\games\bbport\test_saves` (copies only; never the player's `E:\games\bloodborne\user\savedata`).
Each fixture folder holds a `savedata` tree that `tools/mp/instances.py` copies into an instance
(`--saves`, or `BB_TEST_SAVES`); `--fresh-saves` copies it again for every run.

| Fixture (`E:\games\bbport\test_saves\...`) | State | Made by |
|---|---|---|
| `savedata` (the default) | Character "visy", level 37, in the Hunter's Dream; Cleric Beast, Gascoigne, Vicar Amelia dead; night (9800 + 9801); lamps of Central Yharnam / Cathedral Ward; Oedon Tomb Key, Old Hunter Bell; no chalice | copy of the user's 2026-10-12 backup |
| `chalice_pthumeru_ritual\savedata` | The default save after the **Pthumeru Chalice ritual at the First Ritual Altar** (Dream gravestone, slot 1: shared fixed dungeon 1110692594440089, glyph `wmqbhonw`, depth 1); Pthumeru Chalice held, Ritual Blood (1) used, 4000 Echoes; standing at the altar | run altar7 below (2026-10-15) |
| `cathedral_day\savedata` | The default save put back **before day -> evening**: 9800 / 9801 off, the Cathedral Ward door event 12400750 off (the door 2401210 is closed and its prompt works again), at the Cathedral Ward lamp 2402950 | run fixture_cw below (2026-10-15) |
| `rom_dead_dream\savedata` | The default save with **Rom dead** (13201800), in the Hunter's Dream: a lamp travel to Moonside Lake (`host_lamp=3202952` / `BB_PARTY_TEST_START_LAMP=3202952`) plays the Blood Moon scene 13201803 right at the arrival (the lamp is inside its trigger) | run fixture_rom2 below (2026-10-15) |
| `blood_moon_yahargul\savedata` | After the **Blood Moon**: 9800..9802 on, Rom dead, 70002802 on, in Yahar'gul (m28_00, the scene's warp 2802958) | run fixture_bm below (2026-10-15) |

Use one for a single instance or the host with `--saves`, e.g.

```
python tools/mp/instances.py run --count 2 --party --fresh-saves --saves E:\games\bbport\test_saves\chalice_pthumeru_ritual\savedata ...
```

For a **different save per instance** (e.g. a guest that has a ritual dungeon and a host that has
none), put the fixture into that instance's own copy before the run: `instances.py setup` copies
`--saves` into `ROOT\instN\user\savedata` only when that folder does not exist, so replace
`ROOT\inst1\user\savedata` with the fixture's `savedata` folder and keep `--fresh-saves` (it copies
`savedata` to `savedata_party`, the folder a party session plays from).

## How a fixture is made (reproducible)

One instance, the default save, `--party` (a host alone), test aids only, then copy
`ROOT\inst0\user\savedata_party` to `E:\games\bbport\test_saves\<name>\savedata` once the game has
saved (its file times; check with `python -I tools/party/save_decode.py <userdata0000> --flags ID,...`).

* **altar7** (`chalice_pthumeru_ritual`): `BB_PAD_FILE=<root>\pad0.txt` (the walk needs the pad
  file) and
  `BB_PARTY_DIRECTOR_TEST=goods=6109:1,goods=7000:2,echoes=5000,approach=-18.27:-16.88:1.3,seq=!cross@Ritual Altar/?cross@Use the Ritual Altar/cross@Search by Chalice Glyph/cross@Select chalice to use/cross@Rite materials/left@Conduct a ritual to create a Chalice Dungeon?/cross/wait/wait`.
  The Dream's ritual altars are gravestones (m21_00 MSB "メッセンジャー_墓石_D..."):
  2100954 "Makeshift Altar" at (-15.26, -5.86, -18.77), 2100955 **First Ritual Altar** at
  (-18.27, -5.43, -16.88), 2100956 at (-20.39, -5.1, -14.14); the chalice set objects 21012x0..x8 sit on
  them. A `stand=` warp onto them does not move the player (the PlayerIns warp keeps the old spot),
  so `approach=` walks there (closed loop on the position) and the `seq=` menu walk starts when it
  arrived (new: `approach` + `seq` without `stand`). Log: `shared fixed chalice dungeon
  1110692594440089 (glyph wmqbhonw ...) made on first use`, "The ritual is finished, and a chalice
  rests upon the altar." on screen.
* **fixture_cw** (`cathedral_day`): `BB_PARTY_PROGRESS_TEST_CLEAR=9800,9801,12400750`,
  `BB_PARTY_TEST_START_LAMP=2402950`.
* **fixture_rom2** (`rom_dead_dream`): `BB_PARTY_PROGRESS_TEST_SET=13201800`,
  `BB_PARTY_TEST_START_LAMP=2102950` (a load in the Dream, so the game saves).
* **fixture_bm** (`blood_moon_yahargul`): `BB_PARTY_PROGRESS_TEST_SET=13201800`,
  `BB_PARTY_TEST_START_LAMP=3202952`, 140 s (the scene 32000000 plays on arrival, then its warp to
  Yahar'gul; the game saves there).
  `BB_PARTY_TEST_START_LAMP=3202952`.

`stand=obj:ENTITY[:DIST[:ANGLE[:BUTTON]]]` (new) stands at a map object as `host_obj` does, then the
button and `seq=`; for objects on the walkable floor (levers, doors).
