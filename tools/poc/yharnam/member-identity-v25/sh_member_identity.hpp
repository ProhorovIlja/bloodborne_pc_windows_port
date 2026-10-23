// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Canonical member name = lowercase hexadecimal UTF-8 bytes of the transport
// online id (emulator/src/core/bloodborne_party.cpp:BoardMemberOfOnlineId).
// This DOES NOT authenticate the account: the ServerLink SignIn callback must
// also be installed and verify the player's credentials.
#include <cstddef>
#include <cstdlib>
#include <string_view>
namespace SeamlessHunt::Identity {
inline bool StrictMode() noexcept {
    static const bool enabled=[] {
        const char* e=std::getenv("SH_STRICT_MEMBER_ID_BINDING");
        return e != nullptr && e[0]=='1' && e[1]=='\0';
    }();
    return enabled;
}
constexpr bool Matches(std::string_view transport_id,
                    std::string_view claimed_member) noexcept {
    if (transport_id.empty() || transport_id.size() > 48 ||
        claimed_member.size()!=transport_id.size()*2) return false;
    constexpr char Hex[]="0123456789abcdef";
    for(std::size_t i=0;i<transport_id.size();++i){
        const unsigned char b=static_cast<unsigned char>(transport_id[i]);
        if(claimed_member[2*i]!=Hex[b>>4] ||
           claimed_member[2*i+1]!=Hex[b&15]) return false;
    }
    return true;
}
constexpr bool Admit(bool strict, bool sign_in_configured,
                  std::string_view transport_id,
                  std::string_view claimed_member) noexcept {
    return !strict || (sign_in_configured && Matches(transport_id,claimed_member));
}
} // namespace SeamlessHunt::Identity
