// SPDX-License-Identifier: GPL-3.0-or-later
// V2: compile with the REAL source patched with
// -DBBHOST_V2_TEST_ENTROPY_FAIL and check the public caller contract.
// Missing OS randomness must never produce a request or plausible TXID.
// The live HLE socket caller is guarded by the source-locked overlay.
#include "net/stun.h"
#include <array>
#include <cassert>
#include <cstdio>
int main() {
    std::array<std::uint8_t,net::stun::kMaxRequest> request{};
    std::array<std::uint8_t,net::stun::kTxid> id{};
    id.fill(0x7a);
    assert(net::stun::build_binding_request(
        request.data(),id.data(),false,nullptr)==0);
    for(auto v:id) assert(v==0);
    id.fill(0x55);
    assert(net::stun::build_binding_request(
        request.data(),id.data(),true,nullptr)==0);
    for(auto v:id) assert(v==0);
    std::puts("SHYT_BBHOST_V2_STUN_OS_ENTROPY_FAIL_CLOSED_PASS");
}
