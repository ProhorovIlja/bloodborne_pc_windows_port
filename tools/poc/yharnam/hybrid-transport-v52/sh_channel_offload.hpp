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
    InvalidEnemyDirection,
    InvalidPacketClass,
    BadChannel,
};

enum class EnemyRole : std::uint8_t { None, Owner, Follower };

// These values are minted/validated by SERVER-SIDE account, team, world and
// game-stream authorization code. A client cannot self-certify a boolean.
// No caller wired to an actual game socket is currently authorized to pass
// "true": the runtime handshake/ticket and reliable-stream migration remain
// missing, so the current game continues entirely through shadNet.
struct ChannelAuthority {
    bool session_grant_verified = false;
    bool both_peers_consented = false;
    bool peer_binding_verified = false;
    bool both_on_same_authorized_team = false;
    bool protocol_compatible = false;
    bool map_known = false;
    bool map_epoch_verified = false;
    bool both_on_same_map = false;
    bool enemy_stream_authorized = false; // validated delegated sender
    // Verified GAME-STREAM switch, including same session epoch, sequence
    // continuity, ACK ownership, retransmit and safe path handover.
    bool reliable_stream_handover_verified = false;
    EnemyRole sender_enemy_role = EnemyRole::None;
    EnemyRole target_enemy_role = EnemyRole::None;
};

struct Decision {
    bool direct_eligible = false;
    OffloadWhy why = OffloadWhy::KeepServerForAuthority;
};

constexpr bool IsLegacyServerOnly(std::uint32_t channel) noexcept {
    // NativeChannelPolicy == Ours or Drop in pinned upstream packet_routes.h:
    // 0x2C items, 0x2F world corrections, 0x27 boss "thanks" kick.
    return channel == 0x2C || channel == 0x2F || channel == 0x27;
}

constexpr bool IsSameMap(std::uint32_t channel) noexcept {
    // Mirror NativeChannelPolicy::SameMap in pinned coop/packet_routes.h.
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

constexpr bool IsOwnerEnemyChannel(std::uint32_t channel) noexcept {
    return channel == 0x05 || channel == 0x29 || channel == 0x36;
}

// The pinned NetSync game link marks channels 0..6 Unreliable, 7+ Reliable.
constexpr bool NativeReliable(std::uint32_t channel) noexcept {
    return channel > 6;
}

constexpr Decision EligibleChannel(std::uint32_t channel, bool reliable,
                                   const ChannelAuthority& authority) noexcept {
    if (channel > kLastChannel)
        return {false, OffloadWhy::BadChannel};
    if (IsLegacyServerOnly(channel))
        return {false, OffloadWhy::KeepServerForAuthority};
    if (reliable != NativeReliable(channel))
        return {false, OffloadWhy::InvalidPacketClass};
    if (!authority.session_grant_verified || !authority.both_peers_consented ||
        !authority.peer_binding_verified || !authority.both_on_same_authorized_team ||
        !authority.protocol_compatible)
        return {false, OffloadWhy::NotAuthenticated};
    // Do NOT strand the bulk of game traffic on VPS indefinitely. Reliable
    // native GameLink frames may go directly ONLY after the *whole stream*
    // (sender, instance, seq/ACK, retransmits and route switch) is proven
    // safe for this exact pair. Merely having a working UDP socket is NOT proof.
    if (reliable && !authority.reliable_stream_handover_verified)
        return {false, OffloadWhy::ReliablePathNotValidated};
    if (!IsSameMap(channel))
        return {true, OffloadWhy::DirectEligible}; // upstream Pass

    if (!authority.map_known || !authority.map_epoch_verified ||
        !authority.both_on_same_map)
        return {false, OffloadWhy::NoCommonMap};

    // Mirror the actual pinned shadNet SameMap owner's routing rules. This
    // matters more than treating arbitrary messages as "safe" because the
    // channel can be semantically directional, even between teammates.
    const EnemyRole sender = authority.sender_enemy_role;
    const EnemyRole target = authority.target_enemy_role;
    if (channel == 0x16 &&
        (sender != EnemyRole::Follower || target != EnemyRole::Owner))
        return {false, OffloadWhy::InvalidEnemyDirection};
    if (channel == 0x17 &&
        (sender != EnemyRole::Owner || target != EnemyRole::Follower))
        return {false, OffloadWhy::InvalidEnemyDirection};
    if (channel == 0x15 &&
        (sender == EnemyRole::Owner || target == EnemyRole::Follower))
        return {false, OffloadWhy::InvalidEnemyDirection};
    if (IsOwnerEnemyChannel(channel)) {
        const bool allowed =
            target == EnemyRole::None ? sender != EnemyRole::Follower :
            target == EnemyRole::Follower ? sender == EnemyRole::Owner :
            false;
        if (!allowed)
            return {false, OffloadWhy::InvalidEnemyDirection};
    }
    // Unlike a static source-only blacklist, movement from whichever member
    // runs the enemy can be valid under the game's dynamic owner/delegation.
    // Require a fresh server-side proof for THIS source of enemy movement.
    if (channel == kEnemyMovement && !authority.enemy_stream_authorized)
        return {false, OffloadWhy::EnemyOwnershipNotVerified};
    return {true, OffloadWhy::DirectEligible};
}

// All game packet classes are eligible for direct delivery when their CURRENT
// shadNet routing policy allows it AND reliable-stream handover is proven.
// On a path change, GameLink ack-only/keepalive frames also need the same
// reliable lane, otherwise the server stays on the hot path for ACK traffic.
constexpr Decision EligibleGameAck(const ChannelAuthority& authority) noexcept {
    if (!authority.session_grant_verified || !authority.both_peers_consented ||
        !authority.peer_binding_verified || !authority.both_on_same_authorized_team ||
        !authority.protocol_compatible)
        return {false, OffloadWhy::NotAuthenticated};
    return authority.reliable_stream_handover_verified
        ? Decision{true, OffloadWhy::DirectEligible}
        : Decision{false, OffloadWhy::ReliablePathNotValidated};
}

struct FrameEntry {
    std::uint32_t channel = 0xFFFFFFFFU;
    bool reliable = true;
};

// Entire game frames only: we never cherry-pick entries from a reliable frame
// and thereby break its ACK/retransmission accounting. One forbidden entry
// retains the entire frame on the server's routing path.
inline Decision EligibleFrame(std::span<const FrameEntry> entries,
                              const ChannelAuthority& authority,
                              bool verified_game_ack_only = false) noexcept {
    if (entries.empty())
        return verified_game_ack_only ? EligibleGameAck(authority)
                                      : Decision{false, OffloadWhy::BadChannel};
    if (entries.size() > 80)
        return {false, OffloadWhy::BadChannel};
    for (const auto& entry : entries) {
        const auto decision = EligibleChannel(entry.channel, entry.reliable, authority);
        if (!decision.direct_eligible)
            return decision;
    }
    return {true, OffloadWhy::DirectEligible};
}

} // namespace SeamlessHunt::Hybrid
