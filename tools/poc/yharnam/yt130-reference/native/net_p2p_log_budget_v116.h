// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V116: preserve the original first-N join packet diagnostics, without
// a forever-growing fetch_add() for every later game UDP datagram.
#include <atomic>
#include <cstdint>

namespace Libraries::Net::PacketLogBudget {
inline bool Take(std::atomic<std::uint32_t>& emitted,
                 std::uint32_t limit) noexcept {
    auto seen = emitted.load(std::memory_order_relaxed);
    while (seen < limit) {
        if (emitted.compare_exchange_weak(
                seen, seen + 1,
                std::memory_order_relaxed, std::memory_order_relaxed)) {
            return true;
        }
    }
    return false;
}
} // namespace Libraries::Net::PacketLogBudget
