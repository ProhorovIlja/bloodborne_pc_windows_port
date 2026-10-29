// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "sh_channel_offload.hpp"
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

// V54: validate the actual SHAD/0x40 native game frame, not only its supplied
// channel descriptors. The caller MUST already have authenticated the DIRECT
// UDP datagram MAC, pair/session epoch, sequence, endpoint and grant.
// This parser does not establish UDP networking and must never enable P2P by
// itself. Until rendezvous exists the runtime still uses shadNet relay.
namespace SeamlessHunt::Hybrid {
namespace Detail {
inline bool U32(std::span<const std::uint8_t> bytes, std::size_t& offset,
                std::uint32_t& out) noexcept {
    if (offset > bytes.size() || bytes.size() - offset < 4)
        return false;
    out = std::uint32_t(bytes[offset]) |
          std::uint32_t(bytes[offset + 1]) << 8 |
          std::uint32_t(bytes[offset + 2]) << 16 |
          std::uint32_t(bytes[offset + 3]) << 24;
    offset += 4;
    return true;
}
inline bool U16(std::span<const std::uint8_t> bytes, std::size_t& offset,
                std::uint16_t& out) noexcept {
    if (offset > bytes.size() || bytes.size() - offset < 2)
        return false;
    out = static_cast<std::uint16_t>(bytes[offset] | (std::uint16_t(bytes[offset + 1]) << 8));
    offset += 2;
    return true;
}
} // namespace Detail

// Candidate validated ONLY when MAC-authenticated peer identity matches the
// game frame sender, and all nested native game packets are route-eligible.
// The V52 selector separately must already have an active DirectReady path;
// if either denies, send via the ORIGINAL server path without rewriting frames.
inline Decision EligibleNativeWireFrame(std::span<const std::uint8_t> bytes,
                                        std::string_view authenticated_sender,
                                        const ChannelAuthority& authority,
                                        bool native_reliable_handover_proven = false) noexcept {
    constexpr std::size_t kMaxDatagram = 4096;
    constexpr std::size_t kPrefix = 9; // two vports, "SHAD", GamePacketsType
    if (bytes.size() < 26 || bytes.size() > kMaxDatagram ||
        authenticated_sender.empty() || authenticated_sender.size() > 255 ||
        bytes[4] != 'S' || bytes[5] != 'H' || bytes[6] != 'A' || bytes[7] != 'D' ||
        bytes[8] != 0x40)
        return {false, OffloadWhy::BadChannel};
    std::size_t off = kPrefix;
    const auto version = bytes[off++];
    const auto sender_length = bytes[off++];
    if (version != 1 || sender_length == 0 ||
        sender_length != authenticated_sender.size() ||
        bytes.size() - off < std::size_t(sender_length) + 14)
        return {false, OffloadWhy::BadChannel};
    for (std::size_t i = 0; i < sender_length; ++i) {
        if (bytes[off + i] != static_cast<std::uint8_t>(authenticated_sender[i]))
            return {false, OffloadWhy::NotAuthenticated};
    }
    off += sender_length;
    std::uint32_t instance = 0, peer_instance = 0, ack = 0;
    if (!Detail::U32(bytes, off, instance) || !Detail::U32(bytes, off, peer_instance) ||
        !Detail::U32(bytes, off, ack))
        return {false, OffloadWhy::BadChannel};
    // V73: a flag in ChannelAuthority is NOT evidence that the game's
    // reliable transport actually migrated its ACK/sequence/retransmit lane.
    // Native runtime must set this independent gate to false until a
    // bidirectional, epoch-scoped GameLink handover is verified. Even a
    // frame carrying only unreliable game entries can acknowledge older
    // reliable traffic via this common ACK header.
    if (!native_reliable_handover_proven && ack != 0)
        return {false, OffloadWhy::ReliablePathNotValidated};
    std::uint16_t count = 0;
    if (!Detail::U16(bytes, off, count) || count > 80)
        return {false, OffloadWhy::BadChannel};
    if (count == 0)
        return !native_reliable_handover_proven
            ? Decision{false, OffloadWhy::ReliablePathNotValidated}
            : (off == bytes.size()
                ? EligibleFrame({}, authority, true)
                : Decision{false, OffloadWhy::BadChannel});
    for (std::uint16_t i = 0; i < count; ++i) {
        if (bytes.size() - off < 9)
            return {false, OffloadWhy::BadChannel};
        const std::uint8_t packet_class = bytes[off++];
        std::uint32_t seq = 0, packet_size = 0;
        if (packet_class > 1 || !Detail::U32(bytes, off, seq) ||
            !Detail::U32(bytes, off, packet_size) ||
            packet_size < 8 || packet_size > bytes.size() - off)
            return {false, OffloadWhy::BadChannel};
        // The GameLink RELIABLE class is server-only until an actual
        // stream route migration is implemented; a claimed world flag
        // cannot authorize it. Mixed-class frames stay intact on relay.
        if (!native_reliable_handover_proven && packet_class == 1)
            return {false, OffloadWhy::ReliablePathNotValidated};
        // NetSync game packet layout: u32 channel, u32 payload byte count.
        std::size_t inner = off;
        std::uint32_t channel = 0, net_size = 0;
        if (!Detail::U32(bytes, inner, channel) || !Detail::U32(bytes, inner, net_size) ||
            net_size != packet_size - 8)
            return {false, OffloadWhy::BadChannel};
        const auto decision = EligibleChannel(channel, packet_class == 1, authority);
        if (!decision.direct_eligible)
            return decision;
        off += packet_size;
    }
    return off == bytes.size()
        ? Decision{true, OffloadWhy::DirectEligible}
        : Decision{false, OffloadWhy::BadChannel};
}
} // namespace SeamlessHunt::Hybrid
