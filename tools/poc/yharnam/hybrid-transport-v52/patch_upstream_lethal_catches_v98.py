#!/usr/bin/env python3
"""V98 backport upstream lKaniel Bloodborne PR410, immutable pin 77e3507.

When a hunter gives up and dies for real, an IsNoDead lethal-catch made
while dead previously stayed queued until the first tick after respawn,
putting the standing hunter immediately down again at the last lamp.
Consume counters on every valid party-death tick BEFORE the Vital switch.
Original Yharnam Together only, no new server wire or live saves.
"""
from __future__ import annotations

GAME_CPP="emulator/src/core/bloodborne_party.cpp"
GAME_H="emulator/src/core/bloodborne_party.h"
DEATH_CPP="emulator/src/core/bloodborne_party_death.cpp"
INTERNAL_H="emulator/src/core/bloodborne_re_internal.h"
FILES=(GAME_CPP,GAME_H,DEATH_CPP,INTERNAL_H)
MARKER="SHYT-V98-UPSTREAM-LETHAL-CATCHES"

def one(body: str, before: str, after: str, label: str)->str:
    found=body.count(before)
    if found!=1:
        raise ValueError(f"V98 pinned source drift {label}: {found} matches")
    return body.replace(before,after,1)

def patch(inputs: dict[str,bytes])->dict[str,bytes]:
    data={}
    for name in FILES:
        if name not in inputs: raise ValueError("V98 original gameplay file absent: "+name)
        data[name]=inputs[name].decode("utf-8")
        if MARKER in data[name]:
            raise ValueError("V98 patch already present in "+name)

    data[GAME_H]=one(data[GAME_H],
        '''// Holding a button for its hold_ms (giving up): fires once per hold.
class HoldToConfirm {'''.replace("its hold_ms", "a button for "+chr(96)+"hold_ms"+chr(96)).replace("a button for a button for", "a button for"),
        '''// SHYT-V98-UPSTREAM-LETHAL-CATCHES
// Always consume the game's lethal-hit counter in the CURRENT vital state.
// Hit checks made on a corpse are discarded, not deferred until respawn.
class LethalCatches {
public:
    bool Take(u32 count, Vital vital);
private:
    u32 seen = 0;
};

// Holding a button for '''+chr(96)+'''hold_ms'''+chr(96)+''' (giving up): fires once per hold.
class HoldToConfirm {''',
        "game's downed-death policy class")

    data[GAME_CPP]=one(data[GAME_CPP],
        '''bool HoldToConfirm::Tick(bool held, s64 now_ms) {''',
        '''// SHYT-V98-UPSTREAM-LETHAL-CATCHES
bool LethalCatches::Take(u32 count, Vital vital) {
    const bool caught = count != seen;
    seen = count;
    return caught && (vital == Vital::Up || vital == Vital::Off);
}

bool HoldToConfirm::Tick(bool held, s64 now_ms) {''',
        "game policy implementation")

    data[INTERNAL_H]=one(data[INTERNAL_H],
        '''    ReviveHits revive_hits;
    u32 seen_catches = 0;
    u32 seen_attacks = 0;''',
        '''    ReviveHits revive_hits;
    LethalCatches lethal_catches; // SHYT-V98-UPSTREAM-LETHAL-CATCHES
    u32 seen_attacks = 0;''',
        "game-owned death session counter")

    data[DEATH_CPP]=one(data[DEATH_CPP],
        '''    bool armed = false;
    bool alive = false;
};

// Without party death the vitals board''',
        '''    bool armed = false;
    bool alive = false;
    bool caught = false; // SHYT-V98-UPSTREAM-LETHAL-CATCHES
};

// Without party death the vitals board''',
        "death tick caught field")

    data[DEATH_CPP]=one(data[DEATH_CPP],
        '''void TickStanding(PartyDeathRun& run, const DeathTick& tick) {
    const u32 catches = party_death_catches.load();
    const bool caught = catches != run.seen_catches;
    run.seen_catches = catches;
    if (caught && tick.alive) {''',
        '''void TickStanding(PartyDeathRun& run, const DeathTick& tick) {
    if (tick.caught && tick.alive) {''',
        "standing check must not re-read old catch")

    data[DEATH_CPP]=one(data[DEATH_CPP],
        '''    ReadLocalAliveState(tick.player, tick.alive);
    if (const u32 uses = lamp_uses.load(); uses != run.seen_lamp_uses) {''',
        '''    ReadLocalAliveState(tick.player, tick.alive);
    // SHYT-V98-UPSTREAM-LETHAL-CATCHES. Take EVERY tick, even while dead
    // or down, before a state transition can wake this hunter at the lamp.
    tick.caught = run.lethal_catches.Take(
        party_death_catches.load(), run.downed.Current());
    if (const u32 uses = lamp_uses.load(); uses != run.seen_lamp_uses) {''',
        "capture before reviving/death state switch")
    return {name:code.encode("utf-8") for name,code in data.items()}
