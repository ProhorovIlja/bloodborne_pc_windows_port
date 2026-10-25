// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>

// V64 source-only shared authorization policy for matchmaking entry points.
// Never wire client-supplied booleans as server verification. All fields in
// MatchAuthority MUST be resolved by the trusted shadNet account/team/room DB.
// Not wired to live shadNet, no client UI, protocol or port changes.
namespace SeamlessHunt::Matchmaking {

enum class Intent : std::uint8_t { Coop, Invasion, Duel };
enum class EntryPoint : std::uint8_t { Menu, Bell, Friends, QuickPlay, RoomBrowser };
enum class Denied : std::uint8_t {
    None,
    AuthenticationRequired,
    AccessBlocked,
    VersionMismatch,
    TargetRoomUnavailable,
    IncompatibleRoom,
    CoopDisabled,
    HostPvpNotAllowed,
    DuelNotAccepted,
    PrivateInvitationRequired,
    FullRoom,
    FullInvaderSlots
};

struct Request {
    Intent intent = Intent::Coop;
    EntryPoint entry = EntryPoint::Menu;
    bool targeted_friend = false;
};

// The calling server, NEVER the client, resolves this structure from real
// authenticated session state. No passwords, personal IPs or account tokens.
struct MatchAuthority {
    bool requester_authenticated = false;
    bool host_session_verified = false;
    bool account_or_host_blocked_requester = false;
    bool protocol_and_mod_versions_compatible = false;
    bool room_joinable = false;  // current map/room active and permitting joins
    bool coop_allowed = false;
    bool pvp_invasions_allowed = false; // explicit host opt-in
    bool duels_allowed = false;
    bool duel_accepted_by_both = false;
    bool explicit_friend_invite_accepted = false;
    std::uint32_t current_occupants = 0;
    std::uint32_t maximum_occupants = 0; // server policy: 5 must not be assumed
    std::uint32_t current_invaders = 0;
    std::uint32_t maximum_invaders = 0;  // may be 0; no implicit invasion slot
};

struct Decision {
    bool eligible = false;
    Denied why = Denied::AuthenticationRequired;
};

// Important: same permission logic for bell, quick match, menu, friends and
// room browser. The entry point only determines UI, never grants authority.
constexpr Decision Evaluate(const Request& req,
                            const MatchAuthority& a) noexcept {
    if (!a.requester_authenticated || !a.host_session_verified)
        return {false, Denied::AuthenticationRequired};
    if (a.account_or_host_blocked_requester)
        return {false, Denied::AccessBlocked};
    if (!a.protocol_and_mod_versions_compatible)
        return {false, Denied::VersionMismatch};
    if (!a.room_joinable)
        return {false, Denied::TargetRoomUnavailable};
    if (a.maximum_occupants == 0 ||
        a.current_occupants >= a.maximum_occupants)
        return {false, Denied::FullRoom};

    if (req.intent == Intent::Coop) {
        if (!a.coop_allowed) return {false, Denied::CoopDisabled};
        if (req.targeted_friend && !a.explicit_friend_invite_accepted)
            return {false, Denied::PrivateInvitationRequired};
        return {true, Denied::None};
    }
    if (req.intent == Intent::Invasion) {
        if (!a.pvp_invasions_allowed)
            return {false, Denied::HostPvpNotAllowed};
        if (a.maximum_invaders == 0 ||
            a.current_invaders >= a.maximum_invaders)
            return {false, Denied::FullInvaderSlots};
        // Targeting a specific friend never bypasses that friend's explicit
        // acceptance even if the target world generally allows invasions.
        if (req.targeted_friend && !a.explicit_friend_invite_accepted)
            return {false, Denied::PrivateInvitationRequired};
        return {true, Denied::None};
    }
    if (req.intent == Intent::Duel) {
        if (!a.duels_allowed || !a.duel_accepted_by_both)
            return {false, Denied::DuelNotAccepted};
        if (req.targeted_friend && !a.explicit_friend_invite_accepted)
            return {false, Denied::PrivateInvitationRequired};
        return {true, Denied::None};
    }
    return {false, Denied::IncompatibleRoom};
}
} // namespace SeamlessHunt::Matchmaking
