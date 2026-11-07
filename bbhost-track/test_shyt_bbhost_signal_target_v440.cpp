// SPDX-License-Identifier: GPL-3.0-or-later
#include "shyt_bbhost_signal_target_v440.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <span>
#include <string>
using Gate=SeamlessHunt::BbhostSignalTargetV440;
using Reason=Gate::Reason;

static std::array<std::uint8_t,Gate::WireLen> Make(const char* from,
                                                     const char* to,
                                                     std::uint8_t kind) {
    std::array<std::uint8_t,Gate::WireLen> p{};
    for(std::size_t i=0;i<Gate::MagicLen;++i)p[i]=Gate::Magic[i];
    p[4]=kind;p[5]=1u;
    for(std::size_t i=0;i<Gate::IdLen && from[i];++i)
        p[Gate::FromAt+i]=static_cast<std::uint8_t>(from[i]);
    for(std::size_t i=0;i<Gate::IdLen && to[i];++i)
        p[Gate::ToAt+i]=static_cast<std::uint8_t>(to[i]);
    for(std::size_t i=Gate::NonceAt;i<Gate::WireLen;++i)
        p[i]=static_cast<std::uint8_t>(i);
    return p;
}
int main() {
    static_assert(Gate::WireLen==46u && Gate::FromAt==6u &&
                  Gate::ToAt==22u && Gate::NonceAt==38u);
    unsigned accepted=0;
    for(auto kind:{1u,2u,3u,4u,0x11u,0x12u,0x13u,0x14u}) {
        auto wire=Make("Hunter01","Eileen_02",static_cast<std::uint8_t>(kind));
        assert(Gate::Inspect(wire,"Eileen_02")==Reason::Accepted);
        assert(Gate::Inspect(wire,"Eileen_03")==Reason::WrongRecipient);
        assert(Gate::Inspect(wire,"hunter01")==Reason::WrongRecipient);
        assert(Gate::Inspect(wire,"") == Reason::EmptyIdentity);
        assert(Gate::Inspect(
             std::span<const std::uint8_t>(wire.data(),wire.size()-1u),
             "Eileen_02")==Reason::Malformed);
        ++accepted;
    }
    assert(accepted==8u);
    auto normal=Make("Hunter01","Eileen_02",1u);
    normal[0]=0xffu;
    assert(Gate::Inspect(normal,"Eileen_02")==Reason::Malformed);
    normal=Make("Hunter01","Eileen_02",0xffu);
    assert(Gate::Inspect(normal,"Eileen_02")==Reason::Malformed);
    normal=Make("Hunter01","Eileen_02",2u);
    normal[Gate::ToAt+8u]=0u;
    normal[Gate::ToAt+10u]='X'; // bytes after early NUL
    assert(Gate::Inspect(normal,"Eileen_02")==Reason::Malformed);
    normal=Make("Hunter01","Eileen_02",2u);
    normal[Gate::FromAt]=0u; // empty/invalid sender
    assert(Gate::Inspect(normal,"Eileen_02")==Reason::Malformed);
    normal=Make("Eileen_02","Eileen_02",1u);
    assert(Gate::Inspect(normal,"Eileen_02")==Reason::Malformed);
    normal=Make("H01","E01",1u);
    assert(Gate::Inspect(normal,"E01")==Reason::Accepted);
    normal=Make("Hunter01","Eileen_02",1u);
    assert(Gate::Inspect(
        std::span<const std::uint8_t>(normal.data(),normal.size()),
        "Eileen_02")==Reason::Accepted);
    // A forged sender string can still pass this format check.
    // THIS IS WHY the check CANNOT authorize a game route.
    auto forged=Make("Imposter01","Eileen_02",0x11u);
    assert(Gate::Inspect(forged,"Eileen_02")==Reason::Accepted);
    std::puts("SHYT_V440_PR217_SOURCE_WIRE_TARGET_ONLY_NOT_AUTHENTICATION_PASS");
}
