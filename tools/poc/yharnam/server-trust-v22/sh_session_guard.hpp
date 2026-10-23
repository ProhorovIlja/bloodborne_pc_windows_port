// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Validates untrusted BBSC co-op metadata at server ingress.
// No periodic scanner, no persistent player tracking, no automatic bans.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <span>
#include <string_view>
#include <utility>

namespace SeamlessHunt::SessionGuard {
inline constexpr std::uint32_t MaxReviveHitEntries = 16;
inline constexpr std::uint32_t MaxSingleReviveTotal = 32'000;
inline constexpr std::int32_t MaxReportedHp = 30'000;
inline constexpr std::uint32_t MaxReportedSupply = 1000;
inline constexpr float MaxMapCoordinate = 1'000'000.0f;

struct ReviveHit {
    std::string_view target{};
    std::uint32_t down = 0;
    std::uint32_t damage = 0;
};
struct VitalsReport {
    std::uint32_t vital = 0; // OFF, UP, DOWN, DEAD
    std::int32_t hp = 0;
    std::int32_t max_hp = 0;
    std::uint32_t vials = 0;
    std::uint32_t bullets = 0;
    bool has_position = false;
    float x = 0, y = 0, z = 0;
};
constexpr bool SafeVitalValues(const VitalsReport& v) noexcept {
    if (v.vital > 3 || v.max_hp < 0 || v.max_hp > MaxReportedHp ||
        v.hp < -MaxReportedHp || v.hp > MaxReportedHp ||
        v.vials > MaxReportedSupply || v.bullets > MaxReportedSupply)
        return false;
    // Damage callbacks can report a negative HP briefly, but a positive HP
    // many times above reported max is not a trustworthy party-health state.
    if (v.max_hp > 0 && v.hp > v.max_hp + 5000)
        return false;
    if (v.has_position) {
        if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(v.z) ||
            std::abs(v.x) > MaxMapCoordinate || std::abs(v.y) > MaxMapCoordinate ||
            std::abs(v.z) > MaxMapCoordinate) return false;
    }
    return true;
}
// A per-player packet may include cumulative revive progress for several
// teammates. Reject duplicate claims about the same target/down cycle.
inline bool SafeReviveHits(std::span<const ReviveHit> hits) noexcept {
    if (hits.size() > MaxReviveHitEntries) return false;
    for (std::size_t i=0;i<hits.size();++i) {
        const auto& hit = hits[i];
        if (hit.target.empty() || hit.target.size() > 64 ||
            hit.damage > MaxSingleReviveTotal)
            return false;
        for (std::size_t j=0;j<i;++j)
            if (hits[j].target==hit.target && hits[j].down==hit.down) return false;
    }
    return true;
}
inline std::uint32_t AddReviveDamage(std::uint32_t existing,
                                     std::uint32_t claim) noexcept {
    const auto sum=std::uint64_t(existing)+std::min(claim,MaxSingleReviveTotal);
    return sum > std::numeric_limits<std::uint32_t>::max()
        ? std::numeric_limits<std::uint32_t>::max()
        : static_cast<std::uint32_t>(sum);
}
inline bool ShouldAudit(std::int64_t now_ms, std::int64_t last_ms) noexcept {
    // Log at most once per linked client / ten seconds. Never auto-ban based
    // on these heuristics because gameplay mods can trigger false positives.
    return last_ms == 0 || (now_ms >= last_ms && now_ms - last_ms >= 10'000);
}
} // namespace SeamlessHunt::SessionGuard
