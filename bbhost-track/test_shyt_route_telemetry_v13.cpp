// SPDX-License-Identifier: GPL-3.0-or-later
// Harmless synthetic route-counter fixture; NO gameplay packets or network.
#include "hle/shyt_route_telemetry_v13.h"
#include <cassert>
#include <cstdint>
#include <cstring>

int main(int argc,char** argv) {
    assert(argc==2);
    const bool on=std::strcmp(argv[1],"enabled")==0;
    assert(shyt_route_audit_enabled_v13()==on);
    shyt_route_account_success_v13(false,120);
    shyt_route_account_success_v13(true,132);
    // V19: distinct real game-header receive accounting (no packet contents).
    shyt_route_account_received_v19(false,88);
    shyt_route_account_received_v19(true,104);
    assert(shyt_route_v13.direct_packets.load()==(on?1u:0u));
    assert(shyt_route_v13.relay_packets.load()==(on?1u:0u));
    assert(shyt_route_v13.direct_wire_bytes.load()==(on?120u:0u));
    assert(shyt_route_v13.relay_wire_bytes.load()==(on?132u:0u));
    assert(shyt_route_v13.all_packets.load()==(on?2u:0u));
    assert(shyt_route_v13.direct_rx_packets.load()==(on?1u:0u));
    assert(shyt_route_v13.relay_rx_packets.load()==(on?1u:0u));
    assert(shyt_route_v13.direct_rx_wire_bytes.load()==(on?88u:0u));
    assert(shyt_route_v13.relay_rx_wire_bytes.load()==(on?104u:0u));
    assert(shyt_route_v13.rx_all_packets.load()==(on?2u:0u));
    return 0;
}
