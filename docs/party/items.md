# Party items and rewards for guests (Phase C3)

Bloodborne 1.09, our port. **All addresses are our offsets** (raw ELF VA of `smoketest/out/eboot.elf`;
bbhost source = ours + 0x400000). Decompiles: Ghidra (`tools/re/decomp.py`); disassembly and byte checks:
capstone over the ELF. Data: `dvdroot_ps4/param/gameparam` (ItemLotParam, EquipParamGoods/Weapon/Protector,
SpEffectParam, GameAreaParam), every EMEVD + EMELD (FROM's event names), `msg/engus/item.msgbnd` (names),
read with `tools/party/flag_tool.py` helpers.

Markers: **[static]** proven from code/data here, **[inferred]** from names/shape, needs one runtime check
(probes in section 8).

"Guest" = a summoned white phantom in the host's world. In code that state is
`isClient = (SprjSessionManager+0x124 == 6) || (NetworkFlow slots(+0x16F8)+0x98 != -1)`, usually combined with
`GSM(0x5556678)+0x1592 == 0` ("I am in someone else's world", see travel.md 1.0).

## 0. Short answers

| Question | Answer |
|---|---|
| Can a guest pick up world treasure (corpse loot)? | **No, it is never created on a guest.** MSB treasure spawn `0x17DC300` returns at `0x17DC3D6` (role 6) / `0x17DC3E3` (slot +0x98 != -1). [static] |
| Enemy drops? | Yes, rolled locally on the guest's machine, but on a client only items with `isGuestDrop = 1` survive: in the data that is only **Blood Vial (1000)** and **Quicksilver Bullets (900)**. Filter at `0x17DD75D`. [static] |
| Boss drops / key items / remembrance-type items (Oedon Tomb Key, Gold Pendant, badges, chalices, umbilical cords, keys)? | **No.** Boss events award with EMEVD `2003[4]`, which a client skips twice: the script jumps past it (`1003[105]` "jump if client") and `0x17DDC50` refuses `hostOnly` lots on a client (`0x17DDCD9..0x17DDD3E`). Keys that are world treasure (Hunter Chief Emblem, Orphanage Key, Iron Door Key, Lunarium Key, Upper Cathedral Key and so on) are not spawned on the guest. [static] |
| NPC quest rewards? | No for EMEVD gifts (`common 9040/9100/9110`, `2003[4]`, host only). Talk-script (ESD) gifts were not analysed. [static for EMEVD] |
| Blood Echoes | Enemy kills: **50 %** for a client (`0x18FC93D`). Boss clear bonus (GameAreaParam): **50 %** for a phantom (`0x1335578..0x1335591`). Black/other phantoms (chr type 2) get no kill echoes (`0x18C5179`). [static] |
| Insight | A white phantom gets **+1 Insight** when the host's boss dies: `BlockClear2` applies SpEffect **4680** (`heroPointDamage = -1`) at `0x13852B1`. The host pays 1 Insight per Beckoning Bell (from_api_schema.md 8). [static; that -1 means +1 is inferred from the name] |
| Bell-related items | Covenant/Vermin lots in `BlockClear2` (5900/5920/5930 = Vermin, 5910/5940/5950 empty) are given with `hostOnly = 0`, so clients get them too. Bells themselves come from per-player Messenger gifts (lot 10010, flag 6622, personal block 6000-8999). [static] |
| Shops, Doll, level-up | Not while summoned. Phantoms cannot use lamps (lamp gate `0x12F8315`, travel.md), and the Dream is host-only for clients (m21 `1003[6]` guards). Shop stock flags are per-player (6000-8999, kept in the own pool in load mode 1). Level, echoes, insight and inventory live in the guest's own `PlayerGameData` (`[[0x553B130]+8]`), so they persist [inferred: not overlaid like flags]. |

## 1. Globals and functions

| Symbol | Address | Notes |
|---|---|---|
| MapItemMan slot | `0x553D6E0` | `*(u64*)slot` is passed as `rdi` to every lot function (`0x17C17F8`, `0x132E484`) |
| SprjGaitem slot | `0x553E990` | instance handles for weapons/armour/gems (`0x1A876D0`, `0x1A88130`) |
| GameDataMan slot | `0x553B130` | `+8` PlayerGameData: `+0x70` stat fed to the roll as a float (luck-like, [inferred]), `+0x84` Insight, `+0x90` level, `+0x94` echoes (clamped to 999,999,999 in `0x131F980`), `+0xA4` remembered chr type, `+0xF8` float boss-clear-bonus accumulator, `+0x328` inventory |
| Chr-type capability table | `0x47348A0` | 14 × 12 bytes indexed by `PlayerGameData+0xA4`; byte **[2]** = "may receive item lots" (types 0, 1, 8 = 1; 2, 3, 4, 5…13 = 0). Users of byte [2]: only `0x17DC300`, `0x17DD0B0`, `0x17DDC50` [static] |
| ItemLot roll | `0x17CEAF0(LotReq*, char checkGlobal, ctx)` | reads ItemLotParam, skips items whose flag is set, rolls with the game RNG (`GSM+0xA78/+0xA80`) |
| Lot result builder | `0x1A8B080(LotReq*)` | the plan's "MapItemMan lot→items": calls the roll, then builds `{flag, rarity, n, {gaitemHandle, count}×n}` records (0x38 each) at `LotReq+0x88`, count at `+0x80`. It does **not** give anything |
| **Award lot to inventory** | **`0x17DDC50(MapItemMan*, int lot, char hostOnly)`** | the give function (section 2.3) |
| Give item list | `0x17D89F0(MapItemMan*, ItemList*)` | inventory add, overflow to storage `0x14D9A80/0x14DA0A0` or dropped on the ground `0x17DA960`, "item get" popup `0x13107B0(1, …)` |
| MSB treasure spawn | `0x17DC300(MapItemMan*, entityHandle, MsbEvent*, pos*, …)` | only for MSB event type 4 (`[rdx+0xC] == 4`, `0x17DC32B`) [inferred: 4 = Treasure as in the DS1 MSB] |
| Enemy-death drop | `0x17DD0B0(MapItemMan*, chrHandle, npc*)` | from `0x18C4F90` (chr death) |
| Hawk-girl drop (EMEVD 2003[34], DS leftover) | `0x17DB8C0` | spawns a lot as a map item |
| Pick up map item | `0x17D8570(MapItemMan*, &handle)` | from the action-button handler `0x12FD880` (vtable slot `0x531CC70`) |
| Remove map item (+ set its pickup flag) | `0x17D6780(MapItemMan*, &handle, char setFlag)` | |
| Echoes for a kill | `0x18C5070` → `0x18FC860(float soul, PlayerIns*, enemy, bool bonus, bool isClient)` | pays through `PlayerIns->vtbl+0x3D0 (AddSoul)` |
| Boss clear bonus | `0x1335400` (Lua "SetClearBonus") fills `+0xF8`; `0x13356C0` (Lua `AddBlockClearBonus`) pays it | |
| Lua `BlockClear2` (boss killed, every player) | `0x13849A0` | then `BlockClear2_1 0x1385470` (guests sent home, travel.md) |
| Lua `GetRateItem` / `GetRateItem_IgnoreMultiPlay` | `0x132E480` (hostOnly = 1) / `0x132E4A0` (hostOnly = 0) | both `→ 0x17DDC50` |

Lua names come from the registration code (`lea rax, fn` followed by the name `lea rdx`): `0x133D337`
(GetRateItem), `0x133D37D`, `0x138E729` (BlockClear2), `0x13421F2` (AddBlockClearBonus).

## 2. From a lot id to the inventory

### 2.1 ItemLotParam row (BB layout, matches the code in 0x17CEAF0) [static]

| Offset | Field |
|---|---|
| `+0x00..0x1F` | `lotItemId01..08` (s32) |
| `+0x20..0x3F` | `lotItemCategory01..08` (0 weapon, 1 protector, 2 accessory/rune, 4 goods, 8 gem) |
| `+0x40..0x4F` | `lotItemBasePoint01..08` (u16 weights) |
| `+0x50..0x5F` | `cumulateLotPoint01..08` |
| `+0x60..0x7F` | `getItemFlagId01..08` (0 = use the lot-wide flag) |
| `+0x80` | **`getItemFlagId`** (lot-wide pickup flag) |
| `+0x84 / +0x88` | `cumulateNumFlagId` / `cumulateNumMax` (drop-counter value) |
| `+0x89` | rarity |
| `+0x8A..0x91` | `lotItemNum01..08` (u8 counts) |
| `+0x92` | u16 bits: `enableLuck01..08` (bits 0-7), `cumulateReset01..08` (bits 8-15) |

**Chains:** the roll keeps going with `lotId+1, +2…` while rows exist (`0x17CEC00`), so a set such as
2110010/2110011 (Gehrman's cap and garb) is one award. **Flag mapping:** item flag =
`getItemFlagIdNN != 0 ? getItemFlagIdNN : getItemFlagId`, plus the request's byte `LotReq+9` (0 for awards,
an NPC-param offset for enemy drops). In the shipped data `getItemFlagId01..08` is always 0, so **the
lot-wide `getItemFlagId` is the flag**. Treasure lots follow `flag = 50,000,000 + lotId` (784 lots; chains
share the first row's flag; all 811 treasure rows are deterministic: one item per row with weight 100).
Overall 1,377 distinct flags over 7,187 lots that have a flag; 50 flags are shared by alternative lots (NPC
NG+ variants such as 34000/34030/34035 → 50001800), so **flag → lot is not unique** outside treasure.
Lots with `getItemFlagId = -1` (boss drops such as Oedon Tomb Key 31000 and Gold Pendant 50000001) have no
pickup flag at all; vanilla relies on the awarding event's own completion flag.

### 2.2 LotReq (stack struct built by every caller) [static]

`+0x00 lotId`, `+0x04 float` (`0x1581830(PlayerGameData+0x70 as float, +0x670)`), `+0x08 u8 checkFlags = 1`,
`+0x09 u8 flagOffset`, `+0x0A u8 rank`, `+0x0C` out count / `+0x10` out records (0x50 each:
`+0 flag, +4 rarity, +5 n, {+8 itemId, +0xC category, +0x10 count, +0x11 slot} × n`), `+0x20..` area
lot-modifier data (`0x553B148` table), `+0x80/+0x88` resolved records (see 1). Freed with `0x1A8AF00`.

The roll (`0x17CEAF0`) has one global gate: if byte `0x553D6D8 != 0` and `checkGlobal == 1` it produces
nothing (meaning unknown; probably a debug switch).

### 2.3 `0x17DDC50(MapItemMan*, int lot, char hostOnly)` — the award [static]

```c
pgd = GameDataMan->+8; if (!pgd) return;
st  = GSM->+0x16F8;
if ((role == 6 || st->+0x98 != -1) && GSM->+0x1592 == 0)  allowed = 0;     // 0x17DDCD9/0x17DDCE2/0x17DDCF4
else allowed = table_0x47348A0[pgd->+0xA4].byte[2];                          // 0x17DDD21
if (!allowed && hostOnly) return;                                            // 0x17DDD3A xor r14b,1 ; 0x17DDD3E je
LotReq r = {lot, luck, checkFlags=1, …};  0x1A8B080(&r);
for each resolved record:
    list = {n, {gaitem, itemId|category<<28, count, -1} × n};
    0x17D89F0(MapItemMan, &list);                       // inventory + popup
    if (record.flag >= 0) tree_bit(record.flag) |= 1;   // direct OR into the *current* flag tree, no SetEventFlag
0x1A8AF00(&r);
```
Callers: EMEVD `2003[4] アイテム取得` (`0x17C17F8`, hostOnly = 1); EMEVD `2003[36]
クライアントでもアイテム取得` "award even on a client" (hostOnly = 0); Lua `GetRateItem` (1) /
`GetRateItem_IgnoreMultiPlay` (0); `DeadInfoMsg_Host 0x1382A50` (lots 5510/5610/5710/5810, 0),
`DeadInfoMsg_ForceJoinBlack 0x1382ED0` (5500/5600/5700/5800, 1), `TextEffectEnd_PK_Success 0x1383AF0`
(16581, 1), `TextEffectEnd_NPCPK_Success 0x1383BD0` (5020, 0; 16581, 1), `BlockClear2 0x13849A0`
(5910/5930/5940/5950, 0).

Note: the flag is written into whatever tree is live. On a guest in load mode 1 that is the host-world
overlay, which is thrown away on return (event_flags.md 3); the item stays. That is how vanilla
`2003[36]` awards (Bloodied Arm Bands and so on) can be obtained twice.

### 2.4 Map items (treasure, enemy drops, shared drops)

* Record kinds (`+0x20 & 0xF`): 1 hawk drop, 2 enemy drop (`0x17D5320`), 3 treasure / object (`0x17D4FB0`);
  `+0x24` Lua event id, `+0x28` pickup flag, `+0x48` u16 flags (`0x40` takeable, `0x80` network-shared),
  `+0x54` n items, entries from `+0x58` (16 bytes each).
* **Treasure** (`0x17DC300`): gate `0x17DC3CF cmp [role],6 / 0x17DC3D6 je`, `0x17DC3DC cmp [st+0x98],-1 /
  0x17DC3E3 jne`, then chr-type byte [2] (`0x17DC411`). A guest never gets the object, so it cannot loot it.
* **Pickup** `0x17D8570`: unshared item → `0x17D6780(…, 1)` (remove; sets `+0x28` flag and fires the `+0x24`
  Lua event only when `!isClient || GSM+0x1592 != 0`, `0x17D6818..0x17D6831`) then `0x17D89F0` (give).
  Shared item (`0x80`) on a client (`0x17D85F4`) → packet `0x2C {1, 5, handle}` to the host via
  `0x1789A40(*0x553D6D0, 0x2C, buf, 8)`; on the host `0x17DE6E0` + give unless role 6 (`0x17D88BB`). Spawning a
  shared item on a client goes the same way (`0x17D8370`, packet 0x2C subtype 3). [static; the host's reply
  path for 0x2C is not traced]
* **Enemy drops** (`0x17DD0B0`): byte [2] gate only (`0x17DD1C3`; types 0/1/8 pass), then
  `isClient` is stored at `0x17DD193` and used once at `0x17DD75D`: a client keeps an item only if its
  equip param has `isGuestDrop` (goods byte 0x47 bit 3, weapon 0x104 bit 4, protector 0xDF bit 0; gems
  0x8C bit 3). Only goods 900 and 1000 have it.

## 3. Phantom/host checks found (one table)

| Site | Check | Effect for a guest |
|---|---|---|
| EMEVD scripts | `1003[105] (label 1, state 1 = client)` before boss awards; `1003[6] (end, client)` in many NPC/treasure events | event skips the award on clients |
| `0x17DDCD9..0x17DDD3E` | isClient && in host world → hostOnly lots refused | no `2003[4]` / `GetRateItem` lots |
| `0x17DC3CF..0x17DC418` | role 6 / slot +0x98 / chr-type byte [2] | no MSB treasure objects |
| `0x17DD186..0x17DD193`, `0x17DD75D` | isClient → `isGuestDrop` filter | only vials/bullets from enemies |
| `0x17D6818..0x17D6831` | isClient && not own world → no pickup flag / Lua event | (unreachable for treasure on a guest) |
| `0x17D85F4`, `0x17D88BB`, `0x17D8370` | role 6 → shared items go through the host (packet 0x2C) | |
| `0x18C5179` | `PlayerIns+0x78 == 2` (invader) → no kill echoes | |
| `0x18C5216/0x18C5220` → `0x18FC93D` | isClient → kill echoes × 0.5 | |
| `0x1335578..0x1335591` | session has members and own chr type not 0/8 → boss clear bonus × 0.5 (`0x4925B1C` = 0.5) | |
| `0x13849A0` (BlockClear2) | branches on `PlayerIns+0x78`: 0 host, 8 own-world grey, 1 white phantom, 2/0xC invaders (leave) | type 1: bonus paid, SpEffect 4680, flag 6006 cleared, Vermin lots |

## 4. What a guest gets in vanilla (summary)

| Source | Host | White phantom (guest) |
|---|---|---|
| Enemy kill echoes | 100 % | 50 % |
| Enemy item drops | full lot | Blood Vials / Quicksilver Bullets only |
| World treasure | yes | not spawned |
| Boss kill: echoes from the boss's NpcParam | 100 % | 50 % |
| Boss kill: GameAreaParam clear bonus (`bonusSoul_*`, for example Gascoigne 2410800 → 4000) | 100 % | 50 % |
| Boss kill: Insight | (host's own boss scripts) | +1 (SpEffect 4680) |
| Boss kill: item lots (keys, badges, chalices, Madman's Knowledge, cords) | yes | none |
| NPC gifts (EMEVD) | yes | none |
| Covenant/Vermin lots from BlockClear2 / PK texts | per rules | yes (hostOnly 0) |
| Flags of anything above | own save | overlay only (lost) |

## 5. Echoes, Insight, levels (Q4)

* Kill echoes: `echoes = soul × (isClient ? 0.5 : 1.0) × (npcFlag ? 1.2 : 1.0) × Π SpEffect soul rates`,
  rounded (constants `0x4927EBC = 1.0`, `0x4927EC0 = 0.5`, `0x4927EC4 = 1.2`) [static].
* Boss bonus: `0x1335400` reads the first u32 of the area row (`0x1F1B4C0`, GameAreaParam `bonusSoul_single`
  [inferred field]), adds the boss's NpcParam soul when the boss has the bonus bit, halves it for phantoms,
  applies SpEffect soul rates, stores it in `PlayerGameData+0xF8`; `BlockClear2` pays it via `AddSoul`
  (`0x13850A0` own world, `0x138525D` phantom).
* Insight: phantom +1 at `0x138528E mov esi,0x1248` / `0x13852B1 call [vtbl+0x3F0]` (SpEffect 4680:
  `heroPointDamage = -1`, `stateInfo = 119`). Bells: Beckoning costs the host 1 (EquipParamGoods 200 +0x38).
* Levels: only at the Doll in one's own Dream; a guest levels between sessions (B1 sends guests to their own
  world on every travel). Nothing for C3 to do.
* Optional parity patches (all byte-verified, only for a "guests earn like the host" party option):

| Patch | Address | Original | Replacement | Effect |
|---|---|---|---|---|
| Full kill echoes for clients | `0x18FC93F` | `75 06` (jne → 0.5) | `90 90` | multiplier always 1.0 |
| Full boss clear bonus for phantoms | `0x1335582` | `74 12` (je skip-halving) | `EB 12` | never halves |
| Full enemy drops for clients | `0x17DD191` | `08 C1` (or cl,al) | `30 C9` (xor cl,cl) | isClient = 0 for the guest-drop filter only (the byte at `[rbp-0x208]` has one reader, `0x17DD75D`) |

## 6. C3 design: host-authoritative lot replay

Goal: every member's own save receives every item lot the host's world hands out (key items, boss drops,
treasure the host picks up, NPC gifts), exactly once, even across crashes and rejoins.

### 6.1 What triggers a replay (host side)

1. **Flagged lots via the C2 flag diff** (covers treasure, keys, chalices, cords, NPC gifts, and ESD gifts
   that were not analysed): every host flag that flips 0→1 in category `item_lot_picked`
   (party_flags.inc; T5 `5AABZnnn` and global `5000xxxx`) is mapped to its lot:
   `lot = flag - 50,000,000` when `ItemLotParam[lot].getItemFlagId == flag` (all treasure), otherwise the
   generated reverse table (`flag → [lots]`; for the 50 shared flags take the lot the hook in 2 captured).
   **C2 must not sync these flags by itself** (syncing without the item loses it, event_flags.md 9); C3 sets
   them by giving.
2. **Hook the entry of `0x17DDC50`** on the host (cheap: all EMEVD/Lua awards): record `(lot, hostOnly)`.
   Broadcast only `hostOnly == 1` lots (clients already get the `0` ones). This is the only source for
   flagless lots (`getItemFlagId == -1`): Oedon Tomb Key 31000, Gold Pendant 50000001, Old Hunter Badge
   15000, Spark/Sword Hunter Badges 50800000/50000010, Mensis Cage 21000, Madman's Knowledge 75002405,
   25700005, 3401802, 3401852, Bold Hunter's Marks 15005/50800005, Bloodshot Eyeballs 21002950, Yellow
   Backbone 50700000, Kin Coldblood 51001900, 25700000/75002400 (item names missing from the FMG), 22502610,
   Tear Stone 14000 (and 9040 NPC slots with flag -1).
3. Deny list (never replay; per-player or repeatable): lots whose flag is in 6000-8999 (Messenger gifts
   10000/10010/10050, DLC/costume 6670-6678; 10040 the Eye of a Blood-drunk Hunter is replayed since
   2026-10-14, quest_audit.md F3), covenant gems `common 9440`, rune/gem use `9500`,
   repeatables `common 9100` / `13501940` (何度でも), DLC messenger hats `12105064`, PvP/covenant lots
   5500-5950, 16581, 5020, chalice-dungeon lots (area 29, flag -1 boss lots 1100xxxxx).

Message: `PARTY_CMD ITEM_LOT {seq, lot, flag (-1 if none), ledgerIdx (-1 if flagged), source}`.

### 6.2 Duplicate prevention

* Flagged lots: the lot's own flag in the guest's **saved pool** is the "already given" bit. The roll
  itself skips set flags (`0x17CEAF0`), so a replay of a lot the guest already has gives nothing.
* Flagless lots: a C3 **ledger** of event flags `60009000 + idx` (T6 global zone 9). That group is in the
  saved pool (key `3 + 9×5 = 48`), not in the vanilla join snapshot, and no EMEVD/param references any id in
  60000000-60009999 [static over all EMEVD + params; ESD unchecked]. `idx` = position in a generated
  table of the flagless host-only lots in 6.1 item 2 (about 30 entries). Set the bit right after the give.
* Host state for catch-up: the host derives its own "awarded" set from its save (pickup flags + the
  completion flags of the awarding events, for example 12411800 for lot 31000). On every (re)join the host
  sends the full set; the guest applies what it lacks. Live messages are only an optimisation; resending is
  always safe.
* Optional symmetry: members' own solo pickups can be pushed to the others the same way (union policy).
* **Bug fixed 2026-10-10 (blocking "Unable to acquire Sword Hunter Badge due to inventory or storage
  max" dialog on a guest).** Root cause: for a flagless lot the guest checked only its **ledger bit**
  `60009000 + idx`. That bit exists only for C3 replays; a lot the guest's save earned by itself (solo play
  before the party, or here two test saves that started as the same copy) has the awarding event's
  completion flag set but no ledger bit, so the host's `items_full` list re-awarded it. Live evidence (run A):
  `gave ... lot 50000010 (ledger 36 = flag 60009036, full)` (goods 4114, Sword Hunter Badge, `maxNum` 1, no
  storage) although the guest's own flag 12411700 (ledger 36's event) was set; likewise lots 29000, 30000,
  31000, 50000001 (done flags 9066, 9067, 12411800, 12401800). The game then refuses the unique item with a
  modal dialog over the reward list. Fixes in `Apply` (party_items.cpp): (1) a ledger lot whose
  `ItemLedgerDoneFlag` is set in the guest's own save only gets its ledger bit; (2) before any award the lot's
  slots are read from the loaded ItemLotParam (`GameParamRow`, lotItemId +0x00, category +0x20, base point
  +0x40, num +0x8A) and every goods slot is checked against the inventory (`0x14D9E80`) and EquipParamGoods
  `maxNum` (+0x36) / `maxRepositoryNum` (+0x49): a unique item already held (`Owned`) or a count that would
  pass the max with no storage room (`Full`) skips the lot and sets its flag / ledger bit instead
  (`ClassifyLotFit`, unit-tested); (3) popups: 8 s between two real awards (skips take no time) and none
  within 15 s of an HP loss (ChrIns +0x3B0 -> +0x20 -> +0xF8). The own-world gate (load mode 0, own-world
  byte 1, session idle or hosting) was re-checked: no award while summoned. Not done: suppressing the
  reward popup itself (`0x17D89F0` opens it; no flag found yet) and a menu-open check.
  Live (2026-10-10): run C1 skipped the five lots above through rule (1) (`this save's own event flag
  12411700 says it was awarded here`, no award, no dialog); run C3's `BB_PARTY_ITEMS_TEST=10010,50000010`
  probe read the ItemLotParam / EquipParamGoods rows and the inventory on both instances: `goods 200: held
  1 + 1 > max 1, no storage` and `goods 4114: held 1 + 1 > max 1` -> `Owned` (the param file type is
  `ITEMLOT_PARAM_ST`, not `ITEM_LOT_PARAM_ST`).
  **Rule (1) replaced (livesync, 2026-10-10):** checking `ItemLedgerDoneFlag` at apply time also skips
  every boss reward the guest never got, because C2 writes the host's boss / event flags into the guest's
  save first (join snapshot at the first steady world, 30 frames, before the 90-frame item gate; live
  flags while summoned): a boss killed together sets 12401800 in the guest's save, then lot 50000001 was
  skipped. Now the save's own history is recorded once as ledger bits before C2 touches it (ledger
  seeding, below) and own-world ledger awards set their bit in the award hook; rules (2) and (3) stay.

### 6.3 Applying on a guest (main thread)

Run from the A5 tick (`SprjFlipper::Update 0x2034770`). Apply only when **in the own world, load mode 0**:
`*(u32*)(EventFlagMan+0x80) == 0`, `GSM+0x1592 == 1`, `SprjSessionManager+0x124` is 0 or 3 (not 4/6/7),
`WorldChrMan(0x553E878)+0x60 != 0`, `GameDataMan+8 != 0`, `*(u64*)0x553D6E0 != 0`, NowLoading byte
`0x556286B == 0`, not inside the save writer. Queue everything that arrives while summoned (mode 1) and apply
it at the next own-world load (B1 brings guests home on every travel, death and boss clear). Reason: in mode 1
the roll reads the host-world overlay, where the host's flag is already set, so the award would be empty, and
any flag it writes is discarded.

```c
// SysV (guest code is sysv_abi), main thread only
typedef void (*AwardLotFn)(void *mapItemMan, int32_t lot, uint8_t hostOnly);
#define AwardLot ((AwardLotFn)(0x800000000ull + 0x17DDC50))
void *mim = *(void **)(0x800000000ull + 0x553D6E0);

if (flag >= 0 ? IsEventFlag(flag) : ledger_bit(idx)) drop();      // 0x13CFC00 / 0x13CFD80
AwardLot(mim, lot, 0);           // rolls with the guest's own flags, gives, shows the popup,
                                 // sets the lot flag in the live tree (= saved pool in mode 0)
if (flag < 0) SetEventFlag(*(void**)(0x800000000ull+0x553B100), 60009000 + idx, 1);   // 0x13CFCC0
```
* `hostOnly = 0` because the caller does the gating; in mode 0 the gate would pass anyway.
* One lot per tick (each award opens a popup), and the next one only after the popup queue drains.
* Inventory full: `0x17D89F0` sends the overflow to storage, then drops it on the ground (`0x17DA960`); the
  flag is set either way (same as vanilla).
* RNG: the roll consumes the game RNG (`GSM+0xA80`) even for single-item lots. That is harmless on a guest in
  its own world.
* Superseded by section 10 (direct give + own pool while summoned). Originally: not recommended: giving while summoned (calling `0x17D89F0` with a hand-built list plus writing the pool bit).
  It needs gaitem handles for weapons/armour (`0x1A876D0`, `0x1A88130`) and racing the overlay.

### 6.4 Interplay with C2 and C4

* Boss-defeated flags synced by C2 make the guest's own boss event never award (its completion flag is set)
  and are why flagless boss lots must come from C3. Order on a guest: C3 apply, then the C2 boss flags (or the
  same tick).
* NPC quests (C2 `npc_quest`, whole blocks later): their gifts arrive through C3 as soon as the host gets them,
  even if the guest's NPC block is not synced yet.
* Endings and NG+ (C4): NG+ variant lots (34000/34030, 43800/43802…) depend on the cycle; the host's lot id is
  used as is.

### 6.5 Peer validation (bbport security pass)

A guest takes a host row (`FilterPeerItems`, `ItemGrantFromPeerAllowed`) only when it is a host source
(award / flag / full), the lot is not denied (6.1 item 3, Chalice), and the tables agree: the lot's
`ITEM_LOT_FLAG` is the row's flag (or the flag's lot is the row's lot), or a flagless row names the ledger
index of its own lot. **A lot outside the tables is refused**, whatever flag comes with it. Earlier builds
took such a "captured" lot once; that is no longer needed and was a hole:

* an honest host never sends one: `ClassifyAward` takes the flag from `ITEM_LOT_FLAG(lot)` (a flagless lot
  outside the ledger is not offered at all), and `ClassifyFlag` maps flags through the same table or the
  host's captures, which only hold table lots. `party_items.inc` lists *every* flagged ItemLotParam row
  outside the Chalice Dungeons, so a flagged row the game can award is always in it;
* the pair is written into the guest's own save: an arbitrary lot award plus an arbitrary event flag set to
  ON (the "done" flag), i.e. a host could flip any story / boss / NPC flag of a guest.

Host and guests run the same game data (1.09) and the same generated tables; a mismatched build loses only
the rows its tables do not know (logged as rejected), never more.

## 7. Patches considered and rejected for C3

| Site | Original | Would do | Why not |
|---|---|---|---|
| `0x17DDD3E` | `0F 84 8F 07 00 00` | `2003[4]` gives on clients | client EMEVD already skips the instruction (`1003[105]`), and the flag lands in the overlay, so items duplicate |
| `0x17DC3D6` / `0x17DC3E3` | `0F 84 A5 0C 00 00` / `0F 85 98 0C 00 00` | spawns treasure on guests | pickups on a guest set no flag (`0x17D6831`), giving infinite loot and a desync with the host's world |

## 8. Probes

* **I1** log `0x17DDC50(lot, hostOnly)` and `0x17D6780` (handle, kind, `+0x28`) on host and guest during a boss
  kill (Gascoigne) and a treasure pickup; confirm the guest gets no call for 31000 and gets 4680 + bonus.
* **I2** guest replay: in its own world call `0x17DDC50(mim, 2400450, 0)` (Hunter Chief Emblem) twice and
  check one item, flag 52400450 set, popup shown.
* **I3** ledger: set 60009000, save, reload, read it back (pool block present in mode 0 and mode 1).
* **I4** echoes: compare a guest's `PlayerGameData+0x94` delta for one enemy with and without patch
  `0x18FC93F`; `+0x84` before/after a boss as a phantom.
* **I5** what flag 6006 (cleared for a phantom in BlockClear2 at `0x13852EE..0x1385339`) and the global byte
  `0x553D6D8` mean; the host-side handler of packet 0x2C.

## 9. Implementation (gpu/shim/party/party_items.{h,cpp})

* Tables: `party_items.inc`, generated by `tools/party/item_tool.py gen-inc GAME`: `ITEM_LOT_FLAG` (1133
  lots with a pickup flag, Chalice Dungeons left out) and `ITEM_LEDGER` (43 flagless host-only `2003[4]`
  lots, the list of 6.1 item 2, with the awarding event's completion flag = event id + slot, for
  example 31000 → 12411800, common 9040 slot 5 → 9045). Ledger indices are append-only (the generator
  keeps the indices of an existing file).
* Ledger range check: `item_tool.py check-ledger GAME` scans every EMEVD (decoded operands and raw bytes),
  the param bnd, the talk ESD and the Lua bnds for any u32/f32/f64 in 60009000..60009999: 0 hits.
* Host: hook at the entry of `0x17DDC50`; `hostOnly == 1` lots in the own world become grants (flagged
  lot → key = flag, ledger lot → key = 60009000 + idx); `OnHostFlagSet(flag)` (C2's
  `progress::SetItemFlagObserver`, registered by `InstallItemsPatches`) maps flags to lots, preferring
  the lot the hook captured for that flag. Every key is sent once (EVENT `items`); a member that
  (re)joins gets EVENT `items_full`, built on the main thread from the host's flags (lot flags and
  ledger done flags) once the host's own world is up.
* Guest: grants are applied one at a time (1.5 s apart) once the gate held 90 frames: world up with a
  known map, no loading screen, flag store load mode 0, `GSM+0x1592 == 1`, session role 0 or 3, game data
  and MapItemMan present. Skip if the done flag is set; else `0x17DDC50(mim, lot, 0)`, then the ledger
  flag. `0x17D89F0` is hooked only to log what our own award adds to the inventory. A skip or a mark
  opens no popup and does not hold the next grant (a rejoin's ~130-lot full list is almost all skips;
  with the 1.5 s spacing on skips too a new lot behind it waited ~200 s - live run, 2026-10-10).
* Ledger seeding (live run 2026-10-10: a guest on its first party session was given lots 29000, 30000,
  31000, 50000001, 50000010 again, which its own save had earned solo): once per save (marker flag
  60009999, the last ledger bit), at the first steady own world and **before** C2 applies any host
  flag (C2's before-apply hook, `progress::SetBeforeApplyHook`), every ledger lot whose done flag the
  save holds gets its ledger bit. Afterwards an own-world `hostOnly` award of a ledger lot (any role)
  sets its bit in the award hook. A save that took C2 host flags before seeding existed may hold host
  boss flags and so skip a ledger lot it never got (dev saves only).
* Guest "mark": a `hostOnly == 0` lot with a flag that the guest receives while summoned (its flag only
  reaches the overlay) is queued as a mark; at home its flag is set (no item) before any replay, so the
  host's later flag report does not duplicate it. The mark lives in memory: a crash before going home
  loses it (one duplicate possible) [known gap].
* Deviation from 6.1 item 3: Ludwig's and Laurence's boss lots 3401800 (flag 6674) and 3401850 (6673)
  are replayed even though their flags are in 6000-8999: a phantom never gets them (`2003[4]` skipped on
  clients) and the flag is the guest's own, so the replay is exact. All other lots with personal flags
  stay denied.
* Parity patches of section 5: written at start in party mode (`BB_PARTY` set) unless
  `BB_PARTY_FULL_REWARDS=0`, each byte-verified.
* Debug: `BB_PARTY_ITEMS_TEST=<lot>[,...]` applies lots once in the own world in any role (it also turns
  on the party layer's tick). Single-instance runs (Continue via `BB_PAD_FILE`, Hunter's Dream, save
  level 37): `2300090` gave goods 1000 (Blood Vial) x1, flag 52300090 set; ledger lot `24020` gave goods
  1110 x2, flag 60009008 set (log of the `0x17D89F0` list). After a restart the first lot of a run is
  skipped ("already given"), ledger or treasure alike; the second one, awarded 1.5 s later, is given again
  together with its vanilla treasure flag: the game saved once after the first item and the test run was
  killed (BB_TIMEOUT) before the next save, so item and flag share the save. The ledger bit is set before
  the award call (cleared again when the award adds nothing) so it is in the same save as the item.
  With `BB_PARTY` set the three parity patches log `applied`.
* Open: whether the 9040-slot completion flags (9045...) are set exactly when the gift is given
  [inferred from the event shape]; NG+ handling of the ledger flags (T6 global zone 9) [unchecked]; the
  `items_full` list also carries `hostOnly == 0` flagged lots, which a guest that was present in an earlier
  session (mark lost) gets a second time.

## 10. Awarding while summoned (seamless play, 2026-10-10/11)

With B2 / fast join a guest stays summoned (role 6, flag store load mode 1) nearly all the time,
so the own-world replay of 6.3 never ran. Now `ItemsTick` has two gates (`ItemApplyModeNow`):
**Home** (6.3, unchanged) and **Summoned** (`world up, no load, load mode 1, own-world byte 0,
role 6, game data`). In Summoned mode a grant is applied without `0x17DDC50` (whose roll reads
the overlay, where the host's flag is set) and without any overlay write:

* "already given": the done flag (lot flag or ledger bit) read from the **own pool**
  (`progress::ReadFlagOwnSave`), never the overlay.
* items: `PlanSummonedLot` over the lot's ItemLotParam chain (`GameParamRow`, rows lot, lot+1...
  as `0x17CEAF0` walks them; per-row flags already in the own pool are skipped). A row with one
  weighted slot (base or cumulate point) is deterministic (1169 of 1176 table lots). The host
  sends what its roll **really** gave: the award hook now **replaces** `0x17DDC50`
  (`ReplacePrologue`), so `GiveListEntry` captures the host's `0x17D89F0` list during the call
  (`[category, id, count]`, EVENT "items" row element 6). Random lots reported by flag or in
  the full list are rolled **once on the host** (`RollLotChain`) so all guests get the same.
  A guest uses the host's list only when every item is a weighted slot of a different chain row
  with a count <= lotItemNum (security: a host cannot hand out other items); else the rows decide.
* give: `GiveItemDirect 0x131CB70(0, category << 28, id, count)` (weapon, armor, rune, goods).
  **Blood gems** (category 8): the gem the host's game generated is recreated on the guest
  (10.1). Only a gem lot without the host's gem data (a random gem lot reported by flag, the
  rejoin full list) still waits for the own world (`GuestItems::Defer`, logged "waits for the
  own world"; the rest of the queue goes on).
* the native **item-get dialog**: `0x16D8850(*0x553B1C0, &inventory gaitem handle, type bits, id,
  count, 0)` - the entry the lot award's give list queues at `0x17D9348` (plus sound 300); the
  handle is the inventory entry's `+0`. Our overlay toast stays only as a fallback when that
  call cannot be made.
* flags: the done flag plus each giving row's flag into the own pool (`WriteFlagOwnSave`,
  C2's mode-1 pool write), written **before** the give.
* the fit rule (unique / full -> flag only) and the popup rules (8 s spacing, no HP loss for
  15 s) are the same as at home. Marks (hostOnly 0 lots received while summoned) are applied at
  once into the own pool (no more "lost on a crash before going home").
* a save request after each give (see below) so items and flags reach the save together.

Save request: the Lua binding **SaveRequest `0x1336DA0`** (registered at `0x1342F89`: if GSM
`+0x1578` "save allowed" then `+0x1548 = 1`, `+0x1547`, `+0x1549 = 1`) asks the game's save task
to write; `GameSaveTick` runs pending requests (C2 mode-1 applies, C3 gives, C4 story writes,
the late-joiner catch-up) at most once per 15 s. Without it the runs below lost everything at
exit (the game had not saved since the join).

Fixtures: `BB_PARTY_ITEMS_HOST_TEST=<lot>,...` (host: awards through the game's `0x17DDC50`,
hostOnly 1, 20 s after a cooperator appeared, 10 s apart), `BB_PARTY_ITEMS_HOST_TEST_FLAGS=<id>,...`
(host: SetEventFlag with the first award), `BB_PARTY_PROGRESS_TEST_READ=<id>,...` (each steady
load: own save / visible values).

Live (2 loopback instances, guest summoned in the host's Dream the whole time):
* host awards 2700120 (weapon 15000000), 2700150 (armor set, chain), 2700110 (goods 1210 x8),
  2700180 (blood gem), 22502610 (random ledger lot): guest `gave ... while summoned (host's item
  list): weapon 15000000 x1 (held 0 -> 1)`, `armor 290000/291000/112000/293000`, `goods 1210 x8
  (held 0 -> 8)`, `goods 1510 x1` (the host's roll), all "own-save flag(s) ... set (pool, load
  mode 1), overlay untouched"; 2700180 "not while summoned (blood gem...); waits for the own world".
* restart (run 4): the guest's first own-world load reads `52700120=1 52700150=1 52700110=1
  60009032=1 12700110=1 12707800=1` (the last two are the host's C2 flags, written while summoned)
  and the full list skips `lot 2700120 ... already given (own-save flag set; 0:15000000 held 1)`,
  `2700150 ... held 1` x4, `2700110 ... 4:1210 held 8` - nothing given twice. New lots in the same
  run: `goods 1000 x2 (held 15 -> 17, item-get dialog)`, `armor 31000/32000/33000 (item-get dialog)`.

### 10.1 Blood gems while summoned (2026-10-11)

How a lot makes a gem [static]: the lot result builder `0x1A8B080` calls, for a category-8
slot, `0x1A88130(out handle, SprjGaitem, LotReq+0x18, LotReq+0x28, LotReq+0x38, slot id)`.
`LotReq+0x18/+0x28/+0x38` are the **area context** `0x17DDC50` fills from the current block
(`*0x553B148`, row `+0x20`: `+0x48` byte, `+0x4C` / `+0x50` ids, `+0x20 -> +0x38` nine id
pairs); `0x1A88130` sums the pairs' rank offsets onto the slot id, looks the GemGenParam row up
(`0x1F1D630`), rolls the effects (`0x1A8F400`, game RNG) and creates the instance
(`0x1A87E20` -> `0x1A87590(out, SprjGaitem, gem id)`: a new SprjGaitem slot, handle
`0xC0800000 | index`, instance `+8` handle, `+0xC` `0x80000000 | gem id`). `0x1A87E20` then
writes the instance data: `+0x18` flags (two bits of the GemGenParam row `+0x8C`), `+0x1C` rank,
`+0x20..+0x34` six GemeffectParam ids (-1 = empty). The handle goes through the give list
`0x17D89F0`, which adds it to the inventory (`0x14CDA70`), queues the item-get dialog entry
`0x16D8850` with that handle and plays sound 300. Instances: `*(0x553E990) + 8 + index * 8`;
references `+0x8008/+0x800C + index * 8` (`0x1A8BAE0` +1, `0x1A8BC00` -1, frees at 0).

So the guest gets **the host's gem**, not a new roll:
* host: `GiveListEntry` (the `0x17D89F0` hook) reads each category-8 entry's instance
  (`ReadGem`: handle check, id, `+0x18..+0x34`) into the grant's item (`GrantItem::gem`). Awards
  (`0x17DDC50`, captured during the call) and pickups (`0x17D8570 -> 0x17D89F0`, host in its own
  world: kept for 120 s and attached when the treasure's flag reaches `OnHostFlagSet`, if it
  fits the lot's rows) both carry it. A random gem lot is never rolled by the host (no instance
  data); EVENT `items` element `[8, id, 1, [flags, rank, e1..e6]]`.
* guest (`PlanSummonedLot`): a gem matches a weighted category-8 slot of an unused row with
  `slot id <= gem id <= slot id + 99` (`kMaxGemIdOffset`; 1.09 steps by 1..3), count 1, gem data
  plausible (flags 0..3, rank 0..1000, effects -1 or 0..99,999,999; `ItemsFromJson` refuses
  anything else). At give time (`GiveGem`): the GemGenParam row of the id and the GemeffectParam
  row of every effect must exist (`GameParamRow`), the three functions are byte-checked, then
  `0x1A87590(&h, SprjGaitem, id)`, the instance data copied to `+0x18`, and the give list
  `0x17D89F0(MapItemMan, {1, h, 0x80000000 | id, 1, -1})` - inventory (or storage / ground), the
  native item-get dialog and its sound, exactly as the host's award; then our reference is
  released (`0x1A8BC00`).

Live (r1, 2 loopback instances, guest summoned in the host's Dream, `BB_PARTY_ITEMS_HOST_TEST=
2700180,2700110`): host `host award #0 lot 2700180 (flag 52700180, award) queued for the party;
items [8:102001x1 [gem 102001 (flags 2, rank 1, effects 1125000 -1 -1 -1 -1 -1)]]`; guest
`inventory add 1/1: item 102001 category 8 count 1 (gaitem 0xc0800062)` and `gave ... lot 2700180
... while summoned (host's item list): blood gem 102001 (flags 2, rank 1, effects 1125000 -1 -1
-1 -1 -1) (inventory add, item-get dialog); own-save flag(s) 52700180 set (pool, load mode 1),
overlay untouched`. Unit tests: `test_gems` (party-items-test).

### 10.2 The item-get dialog (2026-10-11)

How it works [static]: the give list `0x17D89F0` (and our `ShowItemGet`) pushes an entry with
`0x16D8850(*0x553B1C0, &handle, type bits, id, count, stored)` (8 pooled nodes at `+0x10`, the
live list at `+8`; sound 300). The ItemGetMenuMan tick `0x16D86E0` (from the in-game menu update
`0x17692F0`) sets **`*0x5562878 + 0x130 = 1`** ("dialog up") while the list is not empty and
clears the list only when the action-button check `0x1CD91F0(0, ActionButtonMan, 0xB, 0x1130,
...)` reports the confirm press (gated by player flag `WorldChrMan+0x60 -> +0x58 -> +0x38 -> +0x41`
bit 7 clear and `*0x5540050`). It is modal: the entries stay until the player confirms. The HUD
tick `0x1BFB2A0` (from `0x1BF9E10`, HUD object `rdi`) copies up to 5 entries a frame into the HUD
model (`*(HUD+0xA88) + 0x1238`, 0x48 per row, count `+0x13A8`; item name text via `0x1C5B540`),
and on the rows' 0 -> n edge with `*0x5578A38 < 1`, `menu+0x84 == 0`, `GSM+0x1544 == 0` sets
`menu+0x25C = 1` and asks for a save (GSM `+0x1547..+0x1549`). The movie itself is drawn by the
Scaleform HUD (the `FrpgMenuDlgItemGet` class names have no direct references).

Live (`BB_PARTY_ITEMGET_PROBE=1`, runs r1-r3 and r6, 2 loopback instances, guest summoned in the
host's Dream, `BB_PARTY_ITEMS_HOST_TEST=2700180,2700110`): on **both** instances, at the host's
vanilla award and at the guest's replay alike: `1 entry in the dialog list, dialog UP, confirm
check armed` -> `2 entries ..., dialog UP`; `HUD model rows 1` -> `2`; open gate `*0x5578A38 0,
menu+0x84 0, GSM+0x1544 0, menu+0x25C 1`. The guest's state is the host's, entry for entry (the
gem through the award's own give list, the other categories through `ShowItemGet`), and it stays
up (nobody presses confirm in the test). Screenshots (`tools/mp/shot.py --watch`, PrintWindow of
the background windows, 0.5 / 3 / 8 / 15 s after the give) still show **no box on either
instance**, including the host's vanilla one: every game-side condition of the dialog holds, so
what is missing is the Scaleform HUD draw of that element in these windowed background test
instances (a port / renderer matter, not party state). Not fixed here; the probe is the tool for
the next step (a foreground run with input to see whether the element ever draws in the port).
Note for shot.py: the watcher only reads log lines written while it runs (start it with the run,
`--seconds` longer than any queue wait).

Bisect (2026-10-11, coordinator's list):
* Window focus: the game cannot see it (`sceSystemServiceGetStatus` always reports foreground;
  `BB_WINDOW_BACKGROUND` only makes the SDL window non-focusable).
* Party patches (fast messages / hidden banners): ruled out - a **solo** run without `BB_PARTY`
  (patches: Skip Online/Offline Choice, Skip Intro, Intel Black Tonemap Fix only; native award via
  `BB_PARTY_ITEMS_TEST`) shows the same: list, dialog up, HUD rows, and no box (r9).
* Upscaler / UI composition: `BB_UPSCALER=none` (no UI composition) - no box either (r12).
* The empty-name movie loads at boot (`open(/app0/dvdroot_ps4/menu/.gfx) -> not found`, x3) are
  the **Skip Intro** patch: it zeroes the logo movie names `Logo_Fromsoft` / `Logo_Jstudio` /
  `Logo_SCE` (0x4999138 / 0x4999154 / 0x499916E, loaded by name through 0x1F604F0 from 0x1F6052D);
  unrelated to the item-get box.
* The box is the `GetItemList` clip of `menu/fe.gfx` (root depth, placed at stage (954, 785),
  bottom centre; sprite 240 = five rows `Item_0_0..Item_4_0`, sprite 239 = one row: background,
  RepositoryIcon, ItemIcon, ItemNum, ItemName; one frame, no animation). The HUD update
  `0x1BF7C20` binds it every frame (`GetItemList`, row template `Item_%d_0`, binder `0x1B16D10`)
  to the HUD model rows through the functor at vtable `0x5344970`, whose row method `0x1C02290`
  sets a row visible with icon, `ItemName` text and `ItemNum` when the row's count (+0x40) > 0.
  Probe (r14, solo): the ingameTop update runs ~30x/s and calls the row method for rows 0..4
  (5 per update) while the model holds the award - the game's whole data path to Scaleform is
  live, and still nothing is drawn at the bottom centre. Next: a frame capture (RenderDoc) of a
  foreground run with the list up, to see whether the row draws are issued and what they render.

**Resolved (2026-10-11): the box was always drawn; the screenshots were cropped.** A full-resolution
dump of the presented frame (`BB_FINAL_DUMP_TRIGGER`, r17, solo) shows the dialog at the bottom
centre: `Poison Knife 8` and the `OK` prompt. `tools/mp/shot.py` ran DPI-unaware: on this 200 %
display `GetClientRect` gave the logical size (416x234) of an 833x468 client while `PrintWindow`
drew physical pixels, so every shot was only the top-left quarter of the frame (the HUD gauges -
which is why nothing looked wrong - but never the bottom-centre box or the top-right Insight /
echoes counter). Fix: `shot.py` makes itself per-monitor DPI aware before enumerating windows.
Frame capture (`BB_CAPTURE_TRIGGER`, r16) agrees: after the give the UI pass gains the row
background (masked by a Scaleform stencil pass) and 4 text draws from the glyph cache.
Live (r18, 2 instances, guest summoned, fixed shot.py, 2 s after each give): host and guest show
the same dialog - `Clear Deep Sea 1` (the host's blood gem, recreated on the guest), then
`Clear Deep Sea 1` + `Poison Knife 8` with `OK`. No game or port change was needed; the
bisect notes above stay as the record of what was ruled out.
