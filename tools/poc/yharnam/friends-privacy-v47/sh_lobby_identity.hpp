// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <string_view>

// The native game names a coop board member with the lowercase hex bytes of
// LocalOnlineId (BoardMemberOfOnlineId). That name is not an authentication
// token. Compare it to the account authenticated by the UDP ServerLink Hello,
// *not* to the game's client-controlled character label.
namespace SeamlessHunt::Identity {
constexpr bool MatchesAuthenticatedMember(std::string_view authenticated_id,
                                          std::string_view claimed_member) noexcept {
    constexpr char hex[] = "0123456789abcdef";
    if (authenticated_id.empty() || authenticated_id.size() > 32 ||
        claimed_member.size() != authenticated_id.size() * 2) {
        return false;
    }
    for (std::size_t i = 0; i < authenticated_id.size(); ++i) {
        const unsigned char byte = static_cast<unsigned char>(authenticated_id[i]);
        if (claimed_member[2 * i] != hex[byte >> 4] ||
            claimed_member[2 * i + 1] != hex[byte & 15]) {
            return false;
        }
    }
    return true;
}
} // namespace SeamlessHunt::Identity
