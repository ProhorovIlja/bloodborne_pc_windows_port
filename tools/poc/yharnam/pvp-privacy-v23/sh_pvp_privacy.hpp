// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V23: PvP room-visibility policy for a FUTURE negotiated server protocol.
// Current protocol 7/8 has no authenticated role / invasion-squad metadata.
// Never use client-reported "I can see him" as server-confirmed spotting.
#include <cstdint>

namespace SeamlessHunt::PvpPrivacy {
inline constexpr std::uint32_t PvpProtocol = 9;
inline constexpr std::int64_t CoarseSpotTtlMs = 1500;
enum class Side : std::uint8_t { None, Hunters, Invaders, Spectators };
enum class Feed : std::uint8_t { PartyHud, Compass, Map, PartyVitals, PreciseCoordinates, CoarseLastSeen };
struct Member {
    std::uint64_t room = 0; // server-issued group/session id
    Side side = Side::None;  // server-authoritative, never client text
    std::uint32_t protocol = 0;
    bool server_role_verified = false;
};
constexpr bool SameSquad(const Member& viewer, const Member& target) noexcept {
    return viewer.room != 0 && viewer.room == target.room &&
           viewer.server_role_verified && target.server_role_verified &&
           viewer.protocol >= PvpProtocol && target.protocol >= PvpProtocol &&
           viewer.side == target.side &&
           (viewer.side == Side::Hunters || viewer.side == Side::Invaders);
}
constexpr bool OpposingSides(const Member& viewer, const Member& target) noexcept {
    return viewer.room != 0 && viewer.room == target.room &&
           viewer.server_role_verified && target.server_role_verified &&
           viewer.protocol >= PvpProtocol && target.protocol >= PvpProtocol &&
           ((viewer.side == Side::Hunters && target.side == Side::Invaders) ||
            (viewer.side == Side::Invaders && target.side == Side::Hunters));
}
constexpr bool MaySendPartyTelemetry(Feed feed, const Member& viewer,
                                     const Member& target) noexcept {
    // Precise party metadata is for same-faction teammates only.
    // Observers, legacy clients and the enemy side never receive it.
    return feed != Feed::CoarseLastSeen && SameSquad(viewer,target);
}
constexpr bool MayShareCoarseSpot(const Member& viewer,const Member& target,
                                  bool server_verified_sighting,
                                  std::int64_t age_ms) noexcept {
    // A server sighting can produce a coarse temporary alert, never exact x/y/z
    // or free realtime HUD/nameplate/compass tracking.
    return OpposingSides(viewer,target) && server_verified_sighting &&
           age_ms >= 0 && age_ms <= CoarseSpotTtlMs;
}
constexpr bool MayFreecam(bool pvp_active, const Member& viewer) noexcept {
    // Deny spectator wall-peeking while a PvP session is active.
    return !pvp_active && viewer.side != Side::Spectators;
}
} // namespace SeamlessHunt::PvpPrivacy
