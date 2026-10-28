// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_unified_matchmaking.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace SeamlessHunt::Matchmaking;

constexpr MatchAuthority Room() {
    MatchAuthority r{};
    r.requester_authenticated = r.host_session_verified =
        r.protocol_and_mod_versions_compatible = r.room_joinable = true;
    r.coop_allowed = r.pvp_invasions_allowed = r.duels_allowed = true;
    r.duel_accepted_by_both = r.explicit_friend_invite_accepted = true;
    r.maximum_occupants = 5; // TEST FIXTURE ONLY, no protocol hardcode
    r.current_occupants = 2;
    r.maximum_invaders = 1;
    return r;
}
static_assert(Evaluate({Intent::Invasion, EntryPoint::Menu, false},Room()).eligible);
static_assert(Evaluate({Intent::Invasion, EntryPoint::Bell, false},Room()).eligible);
static_assert(Evaluate({Intent::Duel, EntryPoint::Friends, true},Room()).eligible);
static_assert(Evaluate({Intent::Coop, EntryPoint::QuickPlay, false},Room()).eligible);

int main() {
    constexpr std::array<EntryPoint,5> entries = {
        EntryPoint::Menu, EntryPoint::Bell, EntryPoint::Friends,
        EntryPoint::QuickPlay, EntryPoint::RoomBrowser
    };
    constexpr std::array<Intent,3> modes = {
        Intent::Coop, Intent::Invasion, Intent::Duel
    };
    // There must be precisely ONE server authorization policy, regardless
    // of whether a player presses a bell, picks a friend or Quick Play.
    for (const auto mode : modes) {
        const auto expected=Evaluate({mode,EntryPoint::Menu,false},Room());
        assert(expected.eligible);
        for (const auto entry : entries) {
            const auto result=Evaluate({mode,entry,false},Room());
            assert(result.eligible==expected.eligible);
            assert(result.why==expected.why);
        }
    }
    // Host can allow friendly co-op without granting hostile invasion.
    auto r=Room();
    r.pvp_invasions_allowed=false;
    for(const auto e:entries) {
        assert(Evaluate({Intent::Coop,e,false},r).eligible);
        const auto inv=Evaluate({Intent::Invasion,e,false},r);
        assert(!inv.eligible && inv.why==Denied::HostPvpNotAllowed);
    }
    // Invasion targeting friends is never a loophole around opt-in.
    r=Room();
    r.explicit_friend_invite_accepted=false;
    for(const auto e:entries) {
        assert(!Evaluate({Intent::Invasion,e,true},r).eligible);
        assert(Evaluate({Intent::Invasion,e,false},r).eligible);
        assert(!Evaluate({Intent::Coop,e,true},r).eligible);
        assert(Evaluate({Intent::Coop,e,false},r).eligible);
        assert(!Evaluate({Intent::Duel,e,true},r).eligible);
    }
    r=Room();r.duel_accepted_by_both=false;
    for(const auto e:entries)
        assert(Evaluate({Intent::Duel,e,false},r).why==Denied::DuelNotAccepted);
    // Host/admin blocks, stale sessions and version mismatches fail CLOSED.
    r=Room();r.account_or_host_blocked_requester=true;
    for(const auto mode:modes)
        for(const auto e:entries)
            assert(Evaluate({mode,e,false},r).why==Denied::AccessBlocked);
    r=Room();r.protocol_and_mod_versions_compatible=false;
    for(const auto mode:modes)
        assert(Evaluate({mode,EntryPoint::Friends,false},r).why==Denied::VersionMismatch);
    r=Room();r.requester_authenticated=false;
    assert(Evaluate({Intent::Invasion,EntryPoint::Bell,false},r).why
        ==Denied::AuthenticationRequired);
    r=Room();r.host_session_verified=false;
    assert(Evaluate({Intent::Invasion,EntryPoint::Friends,false},r).why
        ==Denied::AuthenticationRequired);
    r=Room();r.room_joinable=false;
    assert(Evaluate({Intent::Coop,EntryPoint::QuickPlay,false},r).why
        ==Denied::TargetRoomUnavailable);
    // Capacity is server-provided; don't silently turn 5 players into an
    // extra invader, spectator or other over-capacity session member.
    r=Room();r.current_occupants=r.maximum_occupants;
    for(const auto mode:modes)
        assert(Evaluate({mode,EntryPoint::Menu,false},r).why==Denied::FullRoom);
    r=Room();r.maximum_invaders=0;
    assert(Evaluate({Intent::Invasion,EntryPoint::Bell,false},r).why
        ==Denied::FullInvaderSlots);
    assert(Evaluate({Intent::Coop,EntryPoint::Bell,false},r).eligible);
    r=Room();r.current_invaders=r.maximum_invaders;
    assert(Evaluate({Intent::Invasion,EntryPoint::QuickPlay,false},r).why
        ==Denied::FullInvaderSlots);
    r=Room();r.maximum_occupants=0;
    assert(!Evaluate({Intent::Invasion,EntryPoint::Menu,false},r).eligible);
    return 0;
}
