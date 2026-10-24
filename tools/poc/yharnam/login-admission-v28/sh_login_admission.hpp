// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// O(1), fixed-memory ingress guard BEFORE password database authentication.
// A small four-way hash set avoids allocating memory for spoofed IPv4 senders.
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <limits>

namespace SeamlessHunt::LoginAdmission {
inline bool Enabled() noexcept {
    const char* const flag = std::getenv("SH_LOGIN_ADMISSION");
    return flag && flag[0] == '1' && flag[1] == '\0';
}

class Bucket {
public:
    constexpr Bucket(std::uint32_t burst = 1, std::uint32_t per_second = 1)
        : capacity_(std::uint64_t(burst) * 1000), refill_per_ms_(per_second),
          tokens_(capacity_) {}
    void Refill(std::int64_t now_ms) noexcept {
        if (last_ms_ < 0) {
            last_ms_ = now_ms;
        } else if (now_ms > last_ms_) {
            // One minute maximum avoids overflow after clocks/time warp.
            const auto elapsed = (static_cast<std::uint64_t>(now_ms) -
                                  static_cast<std::uint64_t>(last_ms_)) > 60000
                                     ? 60000u
                                     : static_cast<std::uint64_t>(now_ms) -
                                           static_cast<std::uint64_t>(last_ms_);
            const auto next = tokens_ + elapsed * refill_per_ms_;
            tokens_ = next > capacity_ ? capacity_ : next;
            last_ms_ = now_ms;
        }
    }
    bool HasToken() const noexcept { return tokens_ >= 1000; }
    void Spend() noexcept { tokens_ -= 1000; }
private:
    std::uint64_t capacity_, refill_per_ms_, tokens_;
    std::int64_t last_ms_ = -1;
};

class Gate {
public:
    static constexpr std::uint32_t IpBurst = 8;
    static constexpr std::uint32_t IpPerSecond = 2;
    static constexpr std::uint32_t GlobalBurst = 24;
    static constexpr std::uint32_t GlobalPerSecond = 6;
    static constexpr std::size_t Groups = 2048;
    static constexpr std::size_t Ways = 4;
    static constexpr std::int64_t LeaseMs = 30000;

    bool Allow(std::uint32_t ip, std::int64_t now_ms) noexcept {
        global_.Refill(now_ms);
        if (!global_.HasToken()) return false;
        auto& group = slots_[Hash(ip) % Groups];
        Slot* slot = nullptr;
        Slot* reusable = nullptr;
        for (auto& candidate : group) {
            if (candidate.occupied && candidate.ip == ip) {
                slot = &candidate;
                break;
            }
            if (!candidate.occupied || (now_ms >= candidate.last_seen_ms &&
                (static_cast<std::uint64_t>(now_ms) -
                 static_cast<std::uint64_t>(candidate.last_seen_ms)) >=
                    static_cast<std::uint64_t>(LeaseMs))) {
                if (!reusable) reusable = &candidate;
            }
        }
        if (!slot) {
            if (!reusable) return false; // collision pressure, fail closed
            slot = reusable;
            slot->ip = ip;
            slot->occupied = true;
            slot->budget = Bucket(IpBurst, IpPerSecond);
        }
        slot->last_seen_ms = now_ms;
        slot->budget.Refill(now_ms);
        if (!slot->budget.HasToken()) return false;
        slot->budget.Spend();
        global_.Spend();
        return true;
    }
private:
    struct Slot {
        std::uint32_t ip = 0;
        std::int64_t last_seen_ms = -1;
        bool occupied = false;
        Bucket budget{IpBurst,IpPerSecond};
    };
    static constexpr std::size_t Hash(std::uint32_t ip) noexcept {
        std::uint32_t h = ip;
        h ^= h >> 16;
        h *= 0x7feb352du;
        h ^= h >> 15;
        h *= 0x846ca68bu;
        h ^= h >> 16;
        return h;
    }
    std::array<std::array<Slot, Ways>, Groups> slots_{};
    Bucket global_{GlobalBurst,GlobalPerSecond};
};
} // namespace SeamlessHunt::LoginAdmission
