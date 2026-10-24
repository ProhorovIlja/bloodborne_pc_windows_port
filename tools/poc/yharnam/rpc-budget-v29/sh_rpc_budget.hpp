// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstddef>
namespace SeamlessHunt::RpcBudget {
inline constexpr std::size_t MaxBufferedRpcBytes = 2u * 1024u * 1024u;
inline constexpr std::size_t MaxSignedInAccounts = 2048;
// Overflow-proof, including if a caller already exceeded the limit.
constexpr bool Fits(std::size_t already, std::size_t incoming,
                    std::size_t limit = MaxBufferedRpcBytes) noexcept {
    return already <= limit && incoming <= limit - already;
}
constexpr bool MustEvictAuthCache(std::size_t count,
                                 std::size_t limit = MaxSignedInAccounts) noexcept {
    return count >= limit;
}
} // namespace SeamlessHunt::RpcBudget
