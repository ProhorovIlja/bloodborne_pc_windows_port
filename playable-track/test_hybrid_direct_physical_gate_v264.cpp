// SPDX-License-Identifier: GPL-2.0-or-later
// V264: exact SHDP physical-layer demux with original 5-seat max peers.
#include "hybrid_direct_physical_gate_v264.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop::SHYTHybrid;
int main() {
    DirectPhysicalGateV264 gate;
    std::vector<std::uint8_t> encrypted(68,0x55);
    for(size_t i=0;i<DirectPhysicalGateV264::WireHeader.size();++i)
        encrypted[i]=DirectPhysicalGateV264::WireHeader[i];
    assert(DirectPhysicalGateV264::CorrectWire(encrypted));
    DirectPhysicalEndpointV264 first{0x0100007f,0x1201,10500};
    assert(!gate.Allows(first,10000,encrypted)); // no grant
    assert(!gate.InstallAuthenticatedEndpoint(first,10500)); // expired
    assert(!gate.InstallAuthenticatedEndpoint({0,0x1201,10500},10000));
    assert(!gate.InstallAuthenticatedEndpoint({first.addr_nbo,0,10500},10000));
    assert(gate.InstallAuthenticatedEndpoint(first,10000));
    assert(gate.Allows(first,10000,encrypted));
    assert(!gate.Allows(first,10500,encrypted));
    assert(!gate.Allows({first.addr_nbo,0x1202,10500},10000,encrypted));

    // A forged SHAD/ordinary unencrypted server frame must NEVER
    // enter the new peer movement queue.
    auto wrong=encrypted;
    wrong[4]='S';wrong[5]='H';wrong[6]='A';wrong[7]='D';
    assert(!gate.Allows(first,10000,wrong));
    wrong=encrypted;wrong[8]=2;
    assert(!gate.Allows(first,10000,wrong));
    wrong=encrypted;wrong.resize(DirectPhysicalGateV264::MaxWire+1);
    assert(!gate.Allows(first,10000,wrong));
    wrong=encrypted;wrong.resize(15);
    assert(!gate.Allows(first,10000,wrong));

    for(unsigned i=1;i<DirectPhysicalGateV264::MaxPeerEndpoints;++i) {
        assert(gate.InstallAuthenticatedEndpoint(
            {0x0100007f,static_cast<std::uint16_t>(0x1201+i),10500},10000));
    }
    // A five-hunter party exposes at most FOUR remote peers per client.
    assert(!gate.InstallAuthenticatedEndpoint({0x0200007f,0x1209,10500},10000));
    // Replacing the SAME endpoint is allowed (short-lived lease refresh).
    assert(gate.InstallAuthenticatedEndpoint({first.addr_nbo,first.port_nbo,11000},10000));
    assert(gate.Allows(first,10700,encrypted));
    gate.Revoke(first);
    assert(!gate.Allows(first,10700,encrypted));
    assert(gate.InstallAuthenticatedEndpoint({0x0200007f,0x1209,10500},10000));
    gate.RevokeAll();
    assert(!gate.Allows({0x0200007f,0x1209,10500},10000,encrypted));
    puts("SHYT_V264_FIVE_PEER_SECURE_UDP_WIRE_DEMUX_PASS");
}
