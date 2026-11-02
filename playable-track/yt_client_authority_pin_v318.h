// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V318: independent trust root for the ORIGINAL YT physical UDP gate.
// A signed grant's advertised key is NOT a trust root. The operator's
// launcher must provision SHYT_P2P_AUTHORITY_PUB_HEX out-of-band from
// the trusted server setup, before running the game. Default = DENY.
// This is public identity metadata, never the server private signing key.
#include "yt_signed_peer_grant_v279.h"
#include <array>
#include <cstdlib>
#include <optional>
#include <string_view>

namespace BloodborneCoop::SHYTHybrid {
namespace GrantPinV318=SignedPeerGrantV279;

inline std::optional<GrantPinV318::PubKey> ParseClientAuthorityPinV318(
    std::string_view hex)
{
    if (hex.size()!=64)return std::nullopt;
    const auto nibble=[](char c)->int {
        if(c>='0' && c<='9')return c-'0';
        if(c>='a' && c<='f')return c-'a'+10;
        if(c>='A' && c<='F')return c-'A'+10;
        return -1;
    };
    GrantPinV318::PubKey pub{};
    for(std::size_t i=0;i<pub.size();++i) {
        const int hi=nibble(hex[2*i]),lo=nibble(hex[2*i+1]);
        if(hi<0 || lo<0)return std::nullopt;
        pub[i]=static_cast<u8>((hi<<4)|lo);
    }
    if(!GrantPinV318::NonZero(pub))return std::nullopt;
    return pub;
}

inline std::optional<GrantPinV318::PubKey> LauncherAuthorityPinV318() {
    // Never load a pin from bbcoop::DirectPeerGrant, raw SHDP packets,
    // rendezvous addresses, an unauthenticated DNS response or a peer.
    const char* const supplied=std::getenv("SHYT_P2P_AUTHORITY_PUB_HEX");
    if(!supplied)return std::nullopt;
    return ParseClientAuthorityPinV318(std::string_view{supplied});
}

inline bool MatchesLauncherAuthorityV318(
    const GrantPinV318::PubKey& claimed_pin)
{
    const auto authority=LauncherAuthorityPinV318();
    return authority && *authority==claimed_pin;
}
} // namespace BloodborneCoop::SHYTHybrid
