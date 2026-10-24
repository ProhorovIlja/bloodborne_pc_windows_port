// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <cstdlib>
namespace SeamlessHunt::ActiveSession {
inline bool Enabled() noexcept {
    const char* flag = std::getenv("SH_ACTIVE_ACCOUNT_REVOCATION");
    return flag && flag[0] == '1' && flag[1] == '\0';
}
inline constexpr std::int64_t VerifyEveryMs = 15000;
inline constexpr unsigned MaxDbChecksPerTick = 8;
constexpr bool Due(std::int64_t last, std::int64_t now) noexcept {
    return last < 0 || (now >= last &&
          static_cast<std::uint64_t>(now) - static_cast<std::uint64_t>(last) >=
          static_cast<std::uint64_t>(VerifyEveryMs));
}
constexpr bool CheckNow(std::int64_t last, std::int64_t now,
                        unsigned db_checked) noexcept {
    return db_checked < MaxDbChecksPerTick && Due(last,now);
}
}
