// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_secure_grant.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;
using SecureOfferDetail::kWireBytes;
static std::array<std::uint8_t,32> Key(std::uint8_t salt){
    std::array<std::uint8_t,32> b{};
    for(unsigned i=0;i<b.size();++i) b[i]=static_cast<std::uint8_t>(i+salt+1);
    return b;
}
static SecurePeerOffer Offer(){
    SecurePeerOffer p{};
    p.sender_account=501;p.recipient_account=502;
    p.session_epoch=701;p.pair_binding=801;p.world_revision=901;
    p.issued_ms=1000;p.expires_ms=2000;
    p.peer_ipv4_nbo=0x01020304;p.peer_port_nbo=44333;
    p.peer_virtual_ipv4_nbo=0x12131415;p.peer_virtual_port_nbo=31314;
    p.direction_key=Key(10);return p;
}
int main(){
    SealedPeerOffers server,recipient,wrong_recipient;
    const auto key=Key(1);
    assert(!server.InstallChannelKey({}));
    assert(!server.InstallChannelKey(std::array<std::uint8_t,32>{}));
    assert(server.InstallChannelKey(key));
    assert(recipient.InstallChannelKey(key));
    assert(wrong_recipient.InstallChannelKey(Key(4)));
    auto p=Offer();
    std::vector<std::uint8_t> message,second;
    assert(server.Seal(p,1000,message));
    assert(message.size()==kWireBytes);
    assert(server.Seal(p,1001,second));
    assert(second.size()==kWireBytes);
    assert(!std::equal(message.begin()+5,message.begin()+17,second.begin()+5));
    assert(std::search(message.begin(),message.end(),
             p.direction_key.begin(),p.direction_key.end())==message.end());
    SecurePeerOffer out{};
    assert(!wrong_recipient.Open(message,502,701,901,1001,out));
    assert(!recipient.Open(message,501,701,901,1001,out)); // wrong audience
    assert(!recipient.Open(message,502,702,901,1001,out)); // session
    assert(!recipient.Open(message,502,701,902,1001,out)); // map epoch
    assert(!recipient.Open(message,502,701,901,999,out)); // not yet issued
    assert(recipient.Open(message,502,701,901,1001,out));
    assert(out.sender_account==501&&out.recipient_account==502);
    assert(out.direction_key==p.direction_key);
    assert(out.peer_ipv4_nbo==p.peer_ipv4_nbo);
    assert(out.peer_port_nbo==p.peer_port_nbo);
    assert(!recipient.Open(message,502,701,901,1001,out)); // nonce replay
    assert(out.sender_account==0 && out.direction_key[0]==0);
    assert(recipient.Open(second,502,701,901,1001,out)); // distinct nonce
    assert(!recipient.Open(second,502,701,901,1001,out));
    assert(!recipient.Open(message,502,701,901,2000,out)); // replay
    SealedPeerOffers expired; assert(expired.InstallChannelKey(key));
    assert(!expired.Open(second,502,701,901,2000,out)); // expiry boundary
    for(std::size_t ix: {std::size_t(0),std::size_t(4),std::size_t(5),
                         std::size_t(17),std::size_t(18),std::size_t(45),
                         kWireBytes-1}){
        auto tampered=message;tampered[ix]^=0x01;
        SealedPeerOffers fresh;assert(fresh.InstallChannelKey(key));
        assert(!fresh.Open(tampered,502,701,901,1001,out));
    }
    for(const auto trunc:{std::size_t(0),std::size_t(1),
                           std::size_t(16),kWireBytes-1}){
        SealedPeerOffers fresh;assert(fresh.InstallChannelKey(key));
        assert(!fresh.Open(std::span<const std::uint8_t>(
                   message.data(),trunc),502,701,901,1001,out));
    }
    auto off=Offer();off.recipient_account=off.sender_account;
    assert(!server.Seal(off,1001,second));
    off=Offer();off.peer_port_nbo=0;
    assert(!server.Seal(off,1001,second));
    off=Offer();off.world_revision=0;
    assert(!server.Seal(off,1001,second));
    off=Offer();off.direction_key.fill(0);
    assert(!server.Seal(off,1001,second));
    off=Offer();off.expires_ms=off.issued_ms+30001;
    assert(!server.Seal(off,1001,second));
    off=Offer();off.expires_ms=off.issued_ms;
    assert(!server.Seal(off,1000,second));
    // The replay cache MUST never evict old nonces under a live exporter
    // key: after 64 accepted offers, fail closed and require TLS rekeying.
    SealedPeerOffers bounded;assert(bounded.InstallChannelKey(key));
    std::vector<std::uint8_t> extra;
    for(unsigned i=0;i<64;++i) {
        assert(server.Seal(p,1001,extra));
        assert(bounded.Open(extra,502,701,901,1001,out));
    }
    assert(server.Seal(p,1001,extra));
    assert(!bounded.Open(extra,502,701,901,1001,out));
    assert(out.sender_account==0);
    server.Clear();recipient.Clear();
    assert(!server.Seal(p,1001,second));
    assert(!recipient.Open(message,502,701,901,1001,out));
    assert(server.InstallChannelKey(Key(2)));
    assert(!server.Open(message,502,701,901,1001,out));
    return 0;
}
