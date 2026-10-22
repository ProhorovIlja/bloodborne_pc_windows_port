// SPDX-License-Identifier: GPL-3.0-or-later
// Boss fights after a party load (0.7.2 known issue 2, docs/party/world_actions.md): which boss state
// a guest's game takes from the host after a load, and when a guest's boss fog counts as walked
// through. Pure logic, no game access (unit test: tests/test_party_bossfog_rules.cpp); the game side
// is party_b2.cpp (the overlay guard: SaveOverlay / RestoreZeroedOverlay) and party_worldact.cpp
// (the guest's fog report, GuestTick).
//
// The boss fog events (every map EMEVD, flag_tool emevd): a boss's state lives in its map's T1 zone 4
// group, 1AAB4xxx - the host-entered flag 1AAB4800 that the boss's start event (`ボスが動き出す`)
// waits on, the guest-entered flag 1AAB4801 its guest-entry event (`ゲストがボス部屋入場_*`) sets,
// the fight's start event 1AAB4802 (boss health bar) - next to the zone 5 / 6 groups (enemy AI,
// boss parts). None of them is saved across a load: the host's own load (a death, a wipe's respawn
// load, a lamp travel) puts them back to zero, the boss stands at its start and its fog is closed,
// as after a vanilla death. A guest's game takes them from the host's join snapshot only (the world
// mirror leaves them out: progress WorldMirrorKey), so after a load they must be the snapshot's.
//
// What went wrong (0.7.1 smoke wipe_late, wiperace run 1): the overlay guard (run 18: a re-sent
// snapshot left the whole overlay zero, the guest replayed the opening) restored EVERY group that
// came back all zero from the copy saved before the load - also the boss's zone 4 group, which the
// host's wipe load had rightly reset to zero. The guest's game then read the fight as running
// (1AAB4800 = 1: its boss start event showed the health bar at the lamp) and its own old
// guest-entered flag (1AAB4801 = 1) as a fresh walk-through, which it reported 3 s after the load:
// the host opened the fight and the boss attacked the party at the lamp.
#pragma once

#include <cstdint>

namespace coop::bossfog {

/// A map's fight-state group: flag block (id / 1000) 1AABZ of type 1, a map (not the global area 0
/// block 0), zone 4 (boss fight, fog, NPC summon), 5 (enemy AI) or 6 (boss parts, traps). Reset by
/// every load of the map; never in the world mirror.
inline bool FightStateBlock(std::uint32_t block) {
    if (block < 10000u || block >= 100000u) {
        return false;
    }
    const std::uint32_t type = block / 10000u, area = block / 100u % 100u, mblock = block / 10u % 10u,
                        zone = block % 10u;
    return type == 1u && !(area == 0u && mblock == 0u) && zone >= 4u && zone <= 6u;
}
inline bool FightStateFlag(std::uint32_t id) {
    return id >= 10000000u && FightStateBlock(id / 1000u);
}

/// Guest, after the host's snapshot was applied for a load into the host's world: the overlay group
/// of `block` came back all zero (`now_zero`); the copy saved before the load had bits in it
/// (`saved_nonzero`). Restore it from that copy? Never a fight-state group: zero is the host's reset
/// state after its load (a restore brought a wiped fight back to the lamp). Every other group: yes
/// (run 18's zeroed overlay: the opening and the Dream flags).
inline bool GuardRestores(std::uint32_t block, bool now_zero, bool saved_nonzero) {
    return now_zero && saved_nonzero && !FightStateBlock(block);
}

/// Guest, its stay in the host's world since the last load: is the guest-entered flag of a boss
/// fog a stale one, not a walk-through? A guest opens a fight only by going through the fog itself
/// (the fog's action, which sets the flag in the guest's game): a 0 -> 1 this game saw during the
/// stay. A flag that already read 1 from the stay's start (`seen_out` false) came with the load,
/// never from this guest's walk: it is not reported to the host (and not taken for "in the boss
/// room" either). `handled`: the flag was reported / dealt with this stay already.
inline bool StaleFogFlag(bool seen_out, bool in, bool handled) {
    return in && !handled && !seen_out;
}

/// The guest's report of a walk-through: a flag seen 0 this stay that reads 1 now, not yet reported.
inline bool FogWalkedThrough(bool seen_out, bool in, bool handled) {
    return in && !handled && seen_out;
}

} // namespace coop::bossfog
