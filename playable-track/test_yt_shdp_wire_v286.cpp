// SPDX-License-Identifier: GPL-2.0-or-later
// V286 actual physical YT SHDP header and total datagram MTU safety.
#include "yt_shdp_wire_v286.h"
#include "hybrid_direct_physical_gate_v264.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop::SHYTHybrid;
int main() {
    assert(DirectPhysicalGateV264::WireHeader==ShdpWireV286::Header);
    assert(DirectPhysicalGateV264::MaxWire==ShdpWireV286::MaxPhysicalBytes);
    for(size_t n: {ShdpWireV286::MinEncryptedBytes,
                   ShdpWireV286::MinEncryptedBytes+1,
                   ShdpWireV286::MaxEncryptedBytes}) {
        const std::vector<std::uint8_t> plaintext(n,0x55);
        const auto framed=ShdpWireV286::Wrap(plaintext);
        assert(framed && framed->size()==n+ShdpWireV286::Header.size());
        assert(DirectPhysicalGateV264::CorrectWire(*framed));
        assert(ShdpWireV286::StartsWithPeerFamily(*framed));
        const auto opened=ShdpWireV286::OpenEnvelope(*framed);
        assert(opened && opened->size()==n);
        assert(std::equal(opened->begin(),opened->end(),plaintext.begin()));
        auto forged=*framed;
        forged[ShdpWireV286::Header.size()-1]=2;
        assert(!ShdpWireV286::OpenEnvelope(forged));
        assert(!DirectPhysicalGateV264::CorrectWire(forged));
        forged=*framed;forged[4]='X';
        assert(!ShdpWireV286::OpenEnvelope(forged));
        forged=*framed;forged.pop_back();
        // A truncated long packet may still pass the outer length guard;
        // the original Noise AEAD verifier must reject its invalid tag.
        if(forged.size()>=ShdpWireV286::Header.size()+
                            ShdpWireV286::MinEncryptedBytes)
            assert(ShdpWireV286::OpenEnvelope(forged));
    }
    const std::vector<std::uint8_t> too_large(
        ShdpWireV286::MaxEncryptedBytes+1,42);
    assert(!ShdpWireV286::Wrap(too_large));
    const std::vector<std::uint8_t> too_small(
        ShdpWireV286::MinEncryptedBytes-1,42);
    assert(!ShdpWireV286::Wrap(too_small));
    assert(!ShdpWireV286::OpenEnvelope({}));
    puts("SHYT_V286_SHDP_PHYSICAL_AEAD_ENVELOPE_MTU_PASS");
}
