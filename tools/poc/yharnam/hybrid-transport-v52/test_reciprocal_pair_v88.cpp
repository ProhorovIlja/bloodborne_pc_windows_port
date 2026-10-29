// SPDX-License-Identifier: GPL-2.0-or-later
// V88 original Qt bidirectional pair admission and separate SHG2 TLS keys.
// Does NOT authorize any real gameplay UDP; no network connector here.
#include "sh_p2p_reciprocal_pair_v88.hpp"
#include "sh_pair_key_schedule_v89.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
#include <vector>
using namespace SeamlessHunt::Hybrid;

static P2PLocalOfferScope ToA() {
    return {"hunter-A","hunter-B",11,22,303,0x0a010101u,45001,
            0x0b010101u,31314};
}
static P2PLocalOfferScope ToB() {
    // Same public WAN address but distinct ports is a valid home-LAN case.
    return {"hunter-B","hunter-A",22,11,303,0x0a010101u,45002,
            0x0b010102u,31315};
}
static std::array<std::uint8_t,32> Key(std::uint8_t salt) {
    std::array<std::uint8_t,32> k{};
    for(unsigned i=0;i<k.size();++i)
        k[i]=static_cast<std::uint8_t>(salt+i);
    return k;
}
int main() {
    auto aa=ToA(),bb=ToB();
    SecurePeerOfferV84 a{},b{};
    assert(P2PReciprocalPairIssuerV88::Prepare(aa,bb,1000,a,b));
    const auto aid=P2PFullIdentityIssuerV84::AccountDigest("hunter-A");
    const auto bid=P2PFullIdentityIssuerV84::AccountDigest("hunter-B");
    assert(aid && bid && *aid!=*bid);
    assert(a.recipient_account==*aid && a.sender_account==*bid);
    assert(b.recipient_account==*bid && b.sender_account==*aid);
    assert(a.session_epoch==11 && b.session_epoch==22);
    assert(a.world_revision==303 && b.world_revision==303);
    assert(a.pair_binding && a.pair_binding==b.pair_binding);
    assert(a.issued_ms==b.issued_ms && a.expires_ms==11000);
    // Both authentic recipients possess the pair master, but NO direct
    // gameplay packet ever uses that raw key: directional KDF required.
    assert(a.direction_key==b.direction_key);
    std::array<std::uint8_t,32> a_tx_probe{},b_rx_probe{},b_tx_probe{},a_rx_probe{};
    std::array<std::uint8_t,32> a_tx_game{},b_rx_game{},a_rx_game{};
    assert(PairKeyScheduleV89::Derive(a,true,PairKeyPurposeV89::NatProbe,
                                     1001,a_tx_probe));
    assert(PairKeyScheduleV89::Derive(b,false,PairKeyPurposeV89::NatProbe,
                                     1001,b_rx_probe));
    assert(a_tx_probe==b_rx_probe);
    assert(PairKeyScheduleV89::Derive(b,true,PairKeyPurposeV89::NatProbe,
                                     1001,b_tx_probe));
    assert(PairKeyScheduleV89::Derive(a,false,PairKeyPurposeV89::NatProbe,
                                     1001,a_rx_probe));
    assert(a_rx_probe==b_tx_probe && a_tx_probe!=b_tx_probe);
    assert(PairKeyScheduleV89::Derive(a,true,PairKeyPurposeV89::GameData,
                                     1001,a_tx_game));
    assert(PairKeyScheduleV89::Derive(b,false,PairKeyPurposeV89::GameData,
                                     1001,b_rx_game));
    assert(PairKeyScheduleV89::Derive(a,false,PairKeyPurposeV89::GameData,
                                     1001,a_rx_game));
    assert(a_tx_game==b_rx_game && a_tx_game!=a_tx_probe &&
           a_tx_game!=a_rx_game);
    auto different_epoch=a;
    different_epoch.pair_binding++;
    std::array<std::uint8_t,32> other{};
    assert(PairKeyScheduleV89::Derive(different_epoch,true,
           PairKeyPurposeV89::NatProbe,1001,other));
    assert(other!=a_tx_probe);
    different_epoch=a;different_epoch.world_revision++;
    assert(PairKeyScheduleV89::Derive(different_epoch,true,
           PairKeyPurposeV89::NatProbe,1001,other));
    assert(other!=a_tx_probe);
    assert(!PairKeyScheduleV89::Derive(a,true,
           PairKeyPurposeV89::NatProbe,11000,other));
    assert((other==std::array<std::uint8_t,32>{}));
    assert(!PairKeyScheduleV89::Derive(a,true,
           static_cast<PairKeyPurposeV89>(77),1001,other));
    assert((other==std::array<std::uint8_t,32>{}));
    assert(a.peer_port_nbo==qToBigEndian(quint16(45001)));
    assert(b.peer_port_nbo==qToBigEndian(quint16(45002)));
    assert(a.peer_virtual_port_nbo==qToBigEndian(quint16(31314)));
    assert(b.peer_virtual_port_nbo==qToBigEndian(quint16(31315)));

    // Server seals each peer's offer within its OWN separately established
    // TLS session wrapping key. It cannot mix recipients, or replay.
    SealedPeerOffersV84 server_a,server_b,client_a,client_b;
    const auto key_a=Key(1),key_b=Key(91);
    assert(server_a.InstallChannelKey(key_a));
    assert(server_b.InstallChannelKey(key_b));
    assert(client_a.InstallChannelKey(key_a));
    assert(client_b.InstallChannelKey(key_b));
    std::vector<std::uint8_t> wire_a,wire_b;
    assert(server_a.Seal(a,1001,wire_a));
    assert(server_b.Seal(b,1001,wire_b));
    assert(wire_a.size()==SecureOfferV84Detail::kWireBytes);
    assert(wire_b.size()==SecureOfferV84Detail::kWireBytes);
    SecurePeerOfferV84 opened_a{},opened_b{};
    // Cross-key/cross-recipient checks fail closed, without consuming
    // either legitimate recipient's first/only accepted grant.
    assert(!client_a.Open(wire_b,*aid,*bid,11,303,1001,opened_a));
    assert(!client_b.Open(wire_a,*bid,*aid,22,303,1001,opened_b));
    assert(client_a.Open(wire_a,*aid,*bid,11,303,1001,opened_a));
    assert(client_b.Open(wire_b,*bid,*aid,22,303,1001,opened_b));
    assert(opened_a.pair_binding==opened_b.pair_binding);
    assert(opened_a.direction_key==opened_b.direction_key);
    assert(!client_a.Open(wire_a,*aid,*bid,11,303,1001,opened_a));
    assert((opened_a.direction_key==std::array<std::uint8_t,32>{}));

    auto valid=aa;
    auto assert_bad=[&](const P2PLocalOfferScope& left,
                        const P2PLocalOfferScope& right) {
        SecurePeerOfferV84 x=a,y=b;
        assert(!P2PReciprocalPairIssuerV88::Prepare(left,right,1000,x,y));
        assert(x.pair_binding==0 && y.pair_binding==0);
        assert((x.direction_key==std::array<std::uint8_t,32>{}));
        assert((y.direction_key==std::array<std::uint8_t,32>{}));
    };
    valid.peer="another-member";assert_bad(valid,bb);
    valid=aa;valid.recipient="hunter-B";assert_bad(valid,bb);
    valid=aa;valid.recipient_epoch++;assert_bad(valid,bb);
    valid=aa;valid.peer_epoch++;assert_bad(valid,bb);
    valid=aa;valid.world_revision++;assert_bad(valid,bb);
    valid=aa;valid.peer_epoch=0;assert_bad(valid,bb);
    valid=aa;valid.physical_ipv4_host=0;assert_bad(valid,bb);
    valid=aa;valid.physical_port_host=0;assert_bad(valid,bb);
    valid=aa;valid.virtual_ipv4_host=0;assert_bad(valid,bb);
    valid=aa;valid.virtual_port_host=0;assert_bad(valid,bb);
    valid=aa;valid.physical_port_host=bb.physical_port_host;assert_bad(valid,bb);
    valid=aa;valid.recipient=QByteArray(65,'x');assert_bad(valid,bb);
    valid=aa;valid.recipient=QByteArray("evil\nhunter");assert_bad(valid,bb);
    valid=aa;assert_bad(valid,valid);
    SecurePeerOfferV84 x{},y{};
    assert(!P2PReciprocalPairIssuerV88::Prepare(aa,bb,0,x,y));
    assert(!P2PReciprocalPairIssuerV88::Prepare(
       aa,bb,(std::numeric_limits<std::uint64_t>::max)()-1,x,y));

    // Revocation of the shared server-side world makes BOTH offers
    // invalid on the recipient's next current-world check.
    SealedPeerOffersV84 new_client;
    assert(new_client.InstallChannelKey(key_a));
    assert(!new_client.Open(wire_a,*aid,*bid,11,304,1001,opened_a));
    assert(!new_client.Open(wire_a,*aid,*bid,12,303,1001,opened_a));
    assert(!new_client.Open(wire_a,*aid,*bid,11,303,11000,opened_a));
    return 0;
}
