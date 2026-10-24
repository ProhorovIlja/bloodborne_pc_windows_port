// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// O(1) per-linked-client rate protection for strict public rooms, applied
// BEFORE protobuf decoding. No periodic tasks or dynamic allocations.
#include <algorithm>
#include <cstddef>
#include <cstdint>
namespace SeamlessHunt::Ingress {
class Budget {
public:
    static constexpr std::uint32_t BurstMessages = 240;
    static constexpr std::uint32_t RateMessagesPerSecond = 120;
    static constexpr std::uint32_t BurstBytes = 16u * 1024u * 1024u;
    static constexpr std::uint32_t BytesPerSecond = 4u * 1024u * 1024u;
    static constexpr std::size_t MaxMessage = 8u * 1024u * 1024u;
    bool Accept(std::size_t size, std::int64_t now_ms) noexcept {
        if (size > MaxMessage) return false;
        if (last_ms_ < 0) {
            last_ms_ = now_ms;
        } else if (now_ms > last_ms_) {
            const auto ms = static_cast<std::uint64_t>(
                std::min<std::int64_t>(now_ms - last_ms_, 4000));
            tokens_milli_ = std::min<std::uint64_t>(
                static_cast<std::uint64_t>(BurstMessages)*1000,
                tokens_milli_ + ms*RateMessagesPerSecond);
            byte_tokens_ = std::min<std::uint64_t>(
                BurstBytes, byte_tokens_ + ms*(BytesPerSecond/1000u));
            last_ms_ = now_ms;
        }
        if (tokens_milli_ < 1000 || byte_tokens_ < size) return false;
        tokens_milli_ -= 1000;
        byte_tokens_ -= size;
        return true;
    }
    std::uint64_t AvailableBytes() const noexcept { return byte_tokens_; }
private:
    std::int64_t last_ms_ = -1;
    std::uint64_t tokens_milli_ = static_cast<std::uint64_t>(BurstMessages)*1000;
    std::uint64_t byte_tokens_ = BurstBytes;
};
} // namespace SeamlessHunt::Ingress
