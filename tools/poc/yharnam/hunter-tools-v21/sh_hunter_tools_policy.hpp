// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>

namespace SeamlessHunt::HunterTools {
// UI toggle is never host-authoritative. Do not allow any save-editor action
// during a team-mode session (including connection in progress).
constexpr bool AllowLocalEdit(bool in_world, bool coop_mode, bool unlocked) noexcept {
    return in_world && !coop_mode && unlocked;
}
constexpr std::int32_t LevelAfter(std::int32_t current, const std::int32_t* before,
                                  const std::int32_t* after, int count) noexcept {
    // Signed 32-bit intermediate math overflowed on malformed imported saves.
    // Bloodborne's normal character level range tops out at 544.
    std::int64_t level = current;
    for (int i = 0; i < count; ++i) {
        level += std::int64_t(after[i]) - before[i];
    }
    return static_cast<std::int32_t>(level < 1 ? 1 : level > 544 ? 544 : level);
}
} // namespace SeamlessHunt::HunterTools
