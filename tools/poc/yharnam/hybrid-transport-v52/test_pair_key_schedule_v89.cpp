// SPDX-License-Identifier: GPL-2.0-or-later
// V89 pure native C++20 directional SHA256-HMAC protocol on OpenSSL and CNG.
#include "sh_pair_key_schedule_v89.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> Id(unsigned start) {
    std::array<std::uint8_t,32> id{};
    for(std::size_t i=0;i<id.size();++i)
        id[i]=static_cast<std::uint8_t>(start+i);
    return id;
}
static SecurePeerOfferV84 Valid() {
    SecurePeerOfferV84 g{};
    g.sender_account=Id(5);
    g.recipient_account=Id(60);
    g.session_epoch=77;
    g.pair_binding=414243;
    g.world_revision=919293;
    g.issued_ms=1000;
    g.expires_ms=2000;
    g.peer_ipv4_nbo=0x04030201;
    g.peer_port_nbo=44123;
    g.peer_virtual_ipv4_nbo=0x0403020a;
    g.peer_virtual_port_nbo=31314;
    g.direction_key=Id(101);
    return g;
}
int main(){
    const auto a=Valid();
    auto b=a;
    b.sender_account=a.recipient_account;
    b.recipient_account=a.sender_account;
    b.session_epoch=88;
    std::array<std::uint8_t,32> a_to_b{},b_from_a{},b_to_a{},a_from_b{};
    assert(PairKeyScheduleV89::Derive(a,true,PairKeyPurposeV89::NatProbe,
                                     1001,a_to_b));
    assert(PairKeyScheduleV89::Derive(b,false,PairKeyPurposeV89::NatProbe,
                                     1001,b_from_a));
    assert(a_to_b==b_from_a);
    assert(PairKeyScheduleV89::Derive(b,true,PairKeyPurposeV89::NatProbe,
                                     1001,b_to_a));
    assert(PairKeyScheduleV89::Derive(a,false,PairKeyPurposeV89::NatProbe,
                                     1001,a_from_b));
    assert(b_to_a==a_from_b);
    assert(a_to_b!=b_to_a);
    std::array<std::uint8_t,32> game{},peer_game{};
    assert(PairKeyScheduleV89::Derive(a,true,PairKeyPurposeV89::GameData,
                                     1001,game));
    assert(PairKeyScheduleV89::Derive(b,false,PairKeyPurposeV89::GameData,
                                     1001,peer_game));
    assert(game==peer_game && game!=a_to_b && game!=b_to_a);
    assert(game!=a.direction_key);
    auto wrong=b;wrong.world_revision++;
    assert(PairKeyScheduleV89::Derive(wrong,false,PairKeyPurposeV89::NatProbe,
                                     1001,peer_game));
    assert(peer_game!=a_to_b);
    wrong=b;wrong.pair_binding++;
    assert(PairKeyScheduleV89::Derive(wrong,false,PairKeyPurposeV89::NatProbe,
                                     1001,peer_game));
    assert(peer_game!=a_to_b);
    wrong=b;wrong.direction_key[31]^=1;
    assert(PairKeyScheduleV89::Derive(wrong,false,PairKeyPurposeV89::NatProbe,
                                     1001,peer_game));
    assert(peer_game!=a_to_b);
    assert(!PairKeyScheduleV89::Derive(a,true,PairKeyPurposeV89::NatProbe,
                                      2000,game));
    assert((game==std::array<std::uint8_t,32>{}));
    wrong=a;wrong.direction_key.fill(0);
    assert(!PairKeyScheduleV89::Derive(wrong,true,PairKeyPurposeV89::NatProbe,
                                      1001,game));
    assert((game==std::array<std::uint8_t,32>{}));
    assert(!PairKeyScheduleV89::Derive(a,true,static_cast<PairKeyPurposeV89>(0),
                                      1001,game));
    assert((game==std::array<std::uint8_t,32>{}));
    return 0;
}
