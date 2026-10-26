#!/usr/bin/env python3
"""Backport original Yharnam Together PR #407 to our older pinned game.

Original source 77e350743a7cb4524cfcc1782fb6e3af64e25b15 has a
*different* flag table from newest upstream. Only exact source-checked
four-file edits are allowed. Doll flag 6700 must stay player-local;
clear a stale 6700 at a party map load only, never during live Doll talk.
https://github.com/lKaniel/bloodborne-server/pull/407
"""
from __future__ import annotations

HEADER="emulator/src/core/bloodborne_flags.h"
STORE="emulator/src/core/bloodborne_flags_store.cpp"
PARTY_H="emulator/src/core/bloodborne_party.h"
PARTY_CPP="emulator/src/core/bloodborne_party.cpp"
FILES=(HEADER,STORE,PARTY_H,PARTY_CPP)
MARKER="SHYT-V97-UPSTREAM-DOLL-6700"

def one(source,old,new,where):
    n=source.count(old)
    if n!=1:
        raise ValueError(f"V97 original source drift in {where}: {n} matches")
    return source.replace(old,new,1)

def patch(files: dict[str,bytes]) -> dict[str,bytes]:
    # Transaction: validate every original file before publishing any.
    code={}
    for name in FILES:
        if name not in files:
            raise ValueError(f"V97 source {name} absent from pinned composer")
        code[name]=files[name].decode("utf-8")
        if MARKER in code[name]:
            raise ValueError(f"V97 already applied to {name}")

    code[HEADER]=one(code[HEADER],
        '''    Range(6680, 6697, FlagOwner::PerPlayer, FlagCarriesHome,
          "had a weapon the Bath shop then sells (OwnedWeaponFlags, common events 6680-6697: "
          "Ludwig's Holy Blade, the DLC weapons): this player's own"),
    Range(9180, 9199, FlagOwner::Session, 0,''',
        '''    Range(6680, 6697, FlagOwner::PerPlayer, FlagCarriesHome,
          "had a weapon the Bath shop then sells (OwnedWeaponFlags, common events 6680-6697: "
          "Ludwig's Holy Blade, the DLC weapons): this player's own"),
    // SHYT-V97-UPSTREAM-DOLL-6700. The Doll's 6700 is a local talk/menu latch,
    // never a host world flag, never carried or shared with other hunters.
    Range(6700, 6700, FlagOwner::PerPlayer, 0,
          "Doll level-up menu open: this game's own transient conversation flag"),
    Range(9180, 9199, FlagOwner::Session, 0,''',
        "old pinned first-rows Dolly classification")
    code[PARTY_H]=one(code[PARTY_H],
        '''std::vector<s32> LightRequestsToClear(u32 packed_map, const std::function<bool(s32)>& on);
// The other player's "set this event flag"''',
        '''std::vector<s32> LightRequestsToClear(u32 packed_map, const std::function<bool(s32)>& on);
// SHYT-V97-UPSTREAM-DOLL-6700: an active Doll talk is never interrupted;
// only a stale 6700 at the start of a party map load can be reset.
constexpr s32 DollLevelUpFlag = 6700;
bool ClearsDollLevelUpFlag(bool party_configured, bool flag_on);
// The other player's "set this event flag"''',
        "original lamp helper followed by local flag methods")
    code[PARTY_CPP]=one(code[PARTY_CPP],
        '''bool RefusesLampLight(s32 flag, std::optional<bool> lamp_character_off) {
    return LampOfLightRequest(flag).has_value() && lamp_character_off.value_or(false);
}

std::vector<s32> LightRequestsToClear''',
        '''bool RefusesLampLight(s32 flag, std::optional<bool> lamp_character_off) {
    return LampOfLightRequest(flag).has_value() && lamp_character_off.value_or(false);
}

bool ClearsDollLevelUpFlag(bool party_configured, bool flag_on) {
    return party_configured && flag_on;
}

std::vector<s32> LightRequestsToClear''',
        "upstream pure map-load decision")
    code[STORE]=one(code[STORE],
        '''void SetGuestPickupsBeforeMapItems() {
    ApplyTeamWorldOnLoad();
    ClearLightRequestsThatLitNothing();''',
        '''// SHYT-V97-UPSTREAM-DOLL-6700: only at a map load, when no Doll talk
// exists. A stuck team-world 6700 would disable each player's Level Up.
void ClearStuckDollLevelUpFlag() {
    if (!ClearsDollLevelUpFlag(party_controller.has_value(), EventFlagOn(DollLevelUpFlag))) {
        return;
    }
    using SetFlag = void PS4_SYSV_ABI (*)(u64, s32, bool);
    reinterpret_cast<SetFlag>(image_base + PartyGhostSetEventFlagOffset)(0, DollLevelUpFlag, false);
    LOG_INFO(Debug, "Bloodborne party: stale Doll level-up flag {} cleared at map {:#x}",
             DollLevelUpFlag, GetCurrentPackedMap());
}

void SetGuestPickupsBeforeMapItems() {
    ApplyTeamWorldOnLoad();
    ClearLightRequestsThatLitNothing();
    ClearStuckDollLevelUpFlag();''',
        "map-load-only flag scrub after world load")
    # A changed error raises before any caller-owned source map mutates.
    return {key:value.encode("utf-8") for key,value in code.items()}
