// SPDX-License-Identifier: GPL-2.0-or-later
// V84 original Qt authoritative scope -> real OpenSSL AEAD SHG2 roundtrip.
#include "sh_p2p_tls_offer_v84.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;
int main() {
    const QByteArray self="recipient";
    const QByteArray peer="peer-A";
    const auto a=P2PFullIdentityIssuerV84::AccountDigest(self);
    const auto b=P2PFullIdentityIssuerV84::AccountDigest(peer);
    assert(a && b && *a!=*b && a->size()==32);
    assert(P2PFullIdentityIssuerV84::AccountDigest(self)==a);
    assert(!P2PFullIdentityIssuerV84::AccountDigest(QByteArray{}));
    assert(!P2PFullIdentityIssuerV84::AccountDigest(QByteArray(65,'x')));
    assert(!P2PFullIdentityIssuerV84::AccountDigest(QByteArray("bad\nid")));
    assert(!P2PFullIdentityIssuerV84::AccountDigest(QByteArray("bad\0id",6)));
    P2PLocalOfferScope scope{self,peer,8001,9002,93001,
                             0x01020304u,41234,0x0a010203u,3658};
    SecurePeerOfferV84 grant{};
    assert(!P2PFullIdentityIssuerV84::Prepare(scope,"attacker",8001,1000,grant));
    assert(!P2PFullIdentityIssuerV84::Prepare(scope,self,8002,1000,grant));
    auto invalid=scope;invalid.recipient=peer;
    assert(!P2PFullIdentityIssuerV84::Prepare(invalid,self,8001,1000,grant));
    invalid=scope;invalid.peer_epoch=0;
    assert(!P2PFullIdentityIssuerV84::Prepare(invalid,self,8001,1000,grant));
    invalid=scope;invalid.world_revision=0;
    assert(!P2PFullIdentityIssuerV84::Prepare(invalid,self,8001,1000,grant));
    invalid=scope;invalid.virtual_port_host=0;
    assert(!P2PFullIdentityIssuerV84::Prepare(invalid,self,8001,1000,grant));
    assert(P2PFullIdentityIssuerV84::Prepare(scope,self,8001,1000,grant));
    assert(grant.sender_account==*b && grant.recipient_account==*a);
    assert(grant.pair_binding!=0 && grant.world_revision==93001);
    assert(grant.expires_ms==11000);
    assert(grant.peer_port_nbo==qToBigEndian(quint16(41234)));
    assert(grant.peer_virtual_port_nbo==qToBigEndian(quint16(3658)));
    std::array<std::uint8_t,32> key{};
    for(std::size_t i=0;i<key.size();++i)
        key[i]=static_cast<std::uint8_t>(i+1);
    SealedPeerOffersV84 sender,receiver;
    assert(sender.InstallChannelKey(key));
    assert(receiver.InstallChannelKey(key));
    std::vector<std::uint8_t> wire;
    assert(sender.Seal(grant,1000,wire));
    SecurePeerOfferV84 opened{};
    assert(receiver.Open(wire,*a,*b,8001,93001,1001,opened));
    assert(opened.sender_account==grant.sender_account);
    assert(opened.direction_key==grant.direction_key);
    assert(!receiver.Open(wire,*a,*b,8001,93001,1001,opened));
    // Two identities sharing their first eight bytes must not be confused.
    auto near=*a;near[31]^=1;
    SealedPeerOffersV84 denied;assert(denied.InstallChannelKey(key));
    assert(!denied.Open(wire,near,*b,8001,93001,1001,opened));
    assert(opened.direction_key==std::array<std::uint8_t,32>{});
    return 0;
}
