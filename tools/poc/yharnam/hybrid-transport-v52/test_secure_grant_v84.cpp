// SPDX-License-Identifier: GPL-2.0-or-later
// V84 side-by-side SHG2 regression. No game socket or live deployment.
#include "sh_secure_grant.hpp"
#include "sh_secure_grant_v84.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <span>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> Id(int seed) {
    std::array<std::uint8_t,32> bytes{};
    for(std::size_t i=0;i<bytes.size();++i)
        bytes[i]=static_cast<std::uint8_t>(seed+static_cast<int>(i));
    return bytes;
}
static SecurePeerOfferV84 Offer() {
    SecurePeerOfferV84 offer{};
    offer.sender_account=Id(11);
    offer.recipient_account=Id(61);
    offer.session_epoch=202;offer.pair_binding=303;offer.world_revision=404;
    offer.issued_ms=1000;offer.expires_ms=2000;
    offer.peer_ipv4_nbo=0x01020304;
    offer.peer_port_nbo=44333;
    offer.peer_virtual_ipv4_nbo=0x0a010203;
    offer.peer_virtual_port_nbo=31314;
    offer.direction_key=Id(121);
    return offer;
}
int main() {
    const auto key=Id(191);
    const auto original=Offer();
    static_assert(SecureOfferV84Detail::kPlaintextBytes==148);
    static_assert(SecureOfferV84Detail::kWireBytes==183);
    static_assert(SecureOfferDetail::kWireBytes==135); // old SHG1 retained
    auto collision=original.recipient_account;
    collision[31]^=0x80;  // same low 64-bit identifier, different full SHA
    assert(!SecureOfferV84Detail::EqualDigest(collision,original.recipient_account));
    SealedPeerOffersV84 server,client;
    assert(!server.InstallChannelKey({}));
    assert(!server.InstallChannelKey(std::array<std::uint8_t,32>{}));
    assert(server.InstallChannelKey(key));
    assert(client.InstallChannelKey(key));
    std::vector<std::uint8_t> wire,second;
    assert(server.Seal(original,1000,wire));
    assert(wire.size()==SecureOfferV84Detail::kWireBytes);
    assert(wire[0]=='S'&&wire[1]=='H'&&wire[2]=='G'&&wire[3]=='2'&&wire[4]==2);
    assert(server.Seal(original,1001,second));
    assert(!std::equal(wire.begin()+5,wire.begin()+17,second.begin()+5));
    SecurePeerOfferV84 opened{};
    auto recv=original.recipient_account,peer=original.sender_account;
    assert(!client.Open(wire,collision,peer,202,404,1001,opened));
    auto bad_peer=peer;bad_peer[29]^=1;
    assert(!client.Open(wire,recv,bad_peer,202,404,1001,opened));
    assert(!client.Open(wire,recv,peer,203,404,1001,opened));
    assert(!client.Open(wire,recv,peer,202,405,1001,opened));
    assert(!client.Open(wire,recv,peer,202,404,999,opened));
    assert((opened.direction_key==std::array<std::uint8_t,32>{}));
    assert(client.Open(wire,recv,peer,202,404,1001,opened));
    assert(opened.sender_account==peer && opened.recipient_account==recv);
    assert(opened.direction_key==original.direction_key);
    assert(!client.Open(wire,recv,peer,202,404,1001,opened));
    assert((opened.direction_key==std::array<std::uint8_t,32>{}));
    assert(client.Open(second,recv,peer,202,404,1001,opened));
    SealedPeerOffersV84 expiry;
    assert(expiry.InstallChannelKey(key));
    assert(!expiry.Open(wire,recv,peer,202,404,2000,opened));
    SealedPeerOffersV84 wrong_key;
    assert(wrong_key.InstallChannelKey(Id(2)));
    assert(!wrong_key.Open(wire,recv,peer,202,404,1001,opened));
    for(std::size_t position : {std::size_t(0),std::size_t(3),
        std::size_t(4),std::size_t(5),std::size_t(17),
        std::size_t(18),std::size_t(37),wire.size()-1}) {
        auto tampered=wire;
        tampered[position]^=1;
        SealedPeerOffersV84 fresh;
        assert(fresh.InstallChannelKey(key));
        assert(!fresh.Open(tampered,recv,peer,202,404,1001,opened));
    }
    for(std::size_t n : {std::size_t(0),std::size_t(1),
        std::size_t(18),wire.size()-1}) {
        SealedPeerOffersV84 fresh;
        assert(fresh.InstallChannelKey(key));
        assert(!fresh.Open(std::span<const std::uint8_t>(wire.data(),n),
                           recv,peer,202,404,1001,opened));
    }
    auto invalid=original;
    invalid.recipient_account=invalid.sender_account;
    assert(!server.Seal(invalid,1001,second));
    invalid=original;invalid.sender_account.fill(0);
    assert(!server.Seal(invalid,1001,second));
    invalid=original;invalid.direction_key.fill(0);
    assert(!server.Seal(invalid,1001,second));
    invalid=original;invalid.expires_ms=invalid.issued_ms+30001;
    assert(!server.Seal(invalid,1001,second));
    // Replay nonces never evict within same 32-byte wrapping key.
    SealedPeerOffersV84 limited;
    assert(limited.InstallChannelKey(key));
    for(unsigned i=0;i<64;++i) {
        assert(server.Seal(original,1001,second));
        assert(limited.Open(second,recv,peer,202,404,1001,opened));
    }
    assert(server.Seal(original,1001,second));
    assert(!limited.Open(second,recv,peer,202,404,1001,opened));
    limited.Clear();
    assert(!limited.Open(wire,recv,peer,202,404,1001,opened));
    // V75 remains independent, never accept a SHG2 record as SHG1.
    SealedPeerOffers old;
    assert(old.InstallChannelKey(key));
    SecurePeerOffer old_offer{};
    assert(!old.Open(wire,61,202,404,1001,old_offer));
    return 0;
}
