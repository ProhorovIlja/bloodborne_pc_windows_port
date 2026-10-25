// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_native_game_identity_v87.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include <string_view>
using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> FromHex(std::string_view s) {
    assert(s.size()==64);
    auto nib=[](char c)->unsigned {return c<='9'?unsigned(c-'0'):unsigned(c-'a'+10);};
    std::array<std::uint8_t,32> digest{};
    for(std::size_t i=0;i<digest.size();++i)
        digest[i]=static_cast<std::uint8_t>((nib(s[2*i])<<4)|nib(s[2*i+1]));
    return digest;
}
int main() {
    const auto expected=FromHex(
        "4663c2312e23d468d89de720704836d238a06e15040f134f5984542df36cf98d");
    const auto peer=FromHex(
        "bb68701f9d75c4eb73fcf187eac73e3d84edbabfdedfec044eabd468a2c43f8c");
    std::array<std::uint8_t,32> digest{};
    assert(NativeGameSelfIdentityV87::Digest("recipient",digest));
    assert(digest==expected); // Exactly Qt SHA256("YT-P2P-V84-ID:recipient")
    assert(NativeGameSelfIdentityV87::Digest("peer-A",digest));
    assert(digest==peer);
    assert(!NativeGameSelfIdentityV87::Digest("",digest));
    assert((digest==std::array<std::uint8_t,32>{}));
    assert(!NativeGameSelfIdentityV87::Digest("a\nb",digest));
    assert(!NativeGameSelfIdentityV87::Digest("a\rb",digest));
    assert(!NativeGameSelfIdentityV87::Digest(std::string_view("a\0b",3),digest));
    assert(!NativeGameSelfIdentityV87::Digest(std::string(65,'x'),digest));
    NativeOfferIdentityV84 identity{expected,peer,8001,93001,true};
    assert(NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient",true,true,identity));
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient",false,true,identity));
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient",true,false,identity));
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "peer-A",true,true,identity));
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient-2",true,true,identity));
    identity.self_account=peer;
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient",true,true,identity));
    identity={expected,peer,8001,93001,false};
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient",true,true,identity));
    identity={expected,peer,8001,0,true};
    assert(!NativeGameSelfIdentityV87::MatchesAcceptedLink(
        "recipient",true,true,identity));
    return 0;
}
