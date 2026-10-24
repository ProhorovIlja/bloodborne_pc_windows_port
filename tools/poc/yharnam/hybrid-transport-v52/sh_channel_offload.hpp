// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstddef>
#include <cstdint>
#include <span>

// V53 source-only offload gate. V10's "Pass only" channel gate correctly
// protects server authority but would route almost all movement via shadNet.
// This gate can additionally allow high-frequency SAME-MAP UNRELIABLE packets
// *only after* the server independently authorizes both identities, room,
// current map/epoch and (for enemies) delegated enemy-stream ownership.
//
// This file DOES NOT replace V10 or enable a direct UDP socket. It is a
// separate policy input for a future authenticated shadNet rendezvous path.
namespace SeamlessHunt::Hybrid {

constexpr std::uint32_t kLastChannel = 0x43;
constexpr std::uint32_t kPlayerMovement = 0x06;
constexpr std::uint32_t kEnemyMovement = 0x04;

enum class OffloadWhy : std::uint8_t {
    DirectEligible,
    KeepServerForAuthority,
    NotAuthenticated,
    NoCommonMap,
    ReliablePathNotValidated,
    EnemyOwnershipNotVerified,
    BadChannel,
};

struct ChannelAuthority {
    bool session_grant_verified = false;
    bool both_peers_consented = false;
    bool peer_binding_verified = false;
    bool both_on_same_authorized_team = false;
    bool protocol_compatible = false;
    bool map_known = false;
    bool map_epoch_verified = false;
    bool both_on_same_map = false;
    bool enemy_stream_authorized = false; // server grants delegated enemy owner only
};

struct Decision {
    bool direct_eligible = false;
    OffloadWhy why = OffloadWhy::KeepServerForAuthority;
};

constexpr bool IsLegacyServerOnly(std::uint32_t channel) noexcept {
    // NativeChannelPolicy == Ours or Drop in pinned upstream packet_routes.h.
    return channel == 0x2C || channel == 0x2F || channel == 0x27;
}

constexpr bool IsSameMap(std::uint32_t channel) noexcept {
    switch (channel) {
    case 0x04: case 0x05: case 0x06: case 0x0E: case 0x0F:
    case 0x12: case 0x14: case 0x15: case 0x16: case 0x17:
    case 0x24: case 0x25: case 0x29: case 0x2A: case 0x2B:
    case 0x2D: case 0x2E: case 0x30: case 0x31: case 0x34:
    case 0x36: case 0x37: case 0x3D: case 0x3E: case 0x40:
    case 0x41:
        return true;
    default:
        return false;
    }
}

constexpr Decision EligibleChannel(std::uint32_t channel, bool reliable,
                                   const ChannelAuthority& authority) noexcept {
    if (channel > kLastChannel)
        return {false, OffloadWhy::BadChannel};
    if (IsLegacyServerOnly(channel))
        return {false, OffloadWhy::KeepServerForAuthority};
    if (!authority.session_grant_verified || !authority.both_peers_consented ||
        !authority.peer_binding_verified || !authority.both_on_same_authorized_team ||
        !authority.protocol_compatible)
        return {false, OffloadWhy::NotAuthenticated};
    // Changing transport for the reliable sequence stream requires separately
    // verified ACK/reorder semantics. Never quietly migrate it here.
    if (reliable)
        return {false, OffloadWhy::ReliablePathNotValidated};
    if (!IsSameMap(channel))
        return {true, OffloadWhy::DirectEligible}; // V10 Pass-only category
    if (channel != kPlayerMovement && channel != kEnemyMovement)
        return {false, OffloadWhy::KeepServerForAuthority};
    if (!authority.map_known || !authority.map_epoch_verified ||
        !authority.both_on_same_map)
        return {false, OffloadWhy::NoCommonMap};
    if (channel == kEnemyMovement && !authority.enemy_stream_authorized)
        return {false, OffloadWhy::EnemyOwnershipNotVerified};
    return {true, OffloadWhy::DirectEligible};
}

// Entire game frames, not arbitrary individual packets: mixed packets stay
// on relay rather than rewriting reliability/sequence or ACK accounting.
// The actual runtime must validate the full native SHAD frame first (V10),
// then supply these authenticated frame entry descriptors.
struct FrameEntry {
    std::uint32_t channel = 0xFFFFFFFFU;
    bool reliable = true;
};

inline Decision EligibleFrame(std::span<const FrameEntry> entries,
                              const ChannelAuthority& authority) noexcept {
    if (entries.empty() || entries.size() > 80)
        return {false, OffloadWhy::BadChannel};
    for (const auto& entry : entries) {
        const auto decision = EligibleChannel(entry.channel, entry.reliable, authority);
        if (!decision.direct_eligible)
            return decision;
    }
    return {true, OffloadWhy::DirectEligible};
}

} // namespace SeamlessHunt::Hybrid
