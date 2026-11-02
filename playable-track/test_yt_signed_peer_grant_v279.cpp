// SPDX-License-Identifier: GPL-2.0-or-later
// V279: genuine pinned YT Monocypher 4.0.3 EdDSA/BLAKE2b.
#include "yt_signed_peer_grant_v279.h"
#include <cassert>
#include <cstdio>
using namespace BloodborneCoop::SHYTHybrid::SignedPeerGrantV279;

int main() {
    PubKey server_pub{};
    SecretKey server_secret{};
    std::array<u8,32> seed{};
    for(size_t i=0;i<seed.size();++i) seed[i]=static_cast<u8>(i+1);
    // Deterministic fixture, never a production server RNG.
    LinkMonocypher::crypto_eddsa_key_pair(
        server_secret.data(),server_pub.data(),seed.data());
    Scope grant{};
    grant.team="hunters-42";
    grant.party="world:old-yharnam";
    grant.sender="hunter-A";
    grant.receiver="hunter-B";
    grant.sender_instance=17;
    grant.receiver_instance=29;
    grant.map=0x101;
    grant.world_epoch=42;
    grant.issued_unix_ms=1810000000000LL;
    grant.expires_unix_ms=1810000020000LL;
    grant.sender_ip_nbo=0x0100007f;
    grant.receiver_ip_nbo=0x0200007f;
    grant.sender_port_nbo=0x1234;
    grant.receiver_port_nbo=0x5678;
    for(size_t i=0;i<grant.responder_noise_pub.size();++i)
        grant.responder_noise_pub[i]=static_cast<u8>(i+9);
    for(size_t i=0;i<grant.grant_nonce.size();++i)
        grant.grant_nonce[i]=static_cast<u8>(100+i);

    const Expect expected{"hunters-42","world:old-yharnam",
                          "hunter-A","hunter-B",17,29,0x101,42};
    assert(Valid(grant));
    const auto wire=EncodeScope(grant);
    assert(wire.size()>150 && wire.size()<450);
    assert(wire[0]=='S' && wire[1]=='H' && wire[2]=='G' &&
           wire[3]=='P' && wire[4]==1);
    auto signed_grant=Sign(grant,server_secret);
    assert(signed_grant);
    const auto good=signed_grant.value();
    assert(Verify(good,server_pub,expected,grant.issued_unix_ms));
    assert(Verify(good,server_pub,expected,grant.expires_unix_ms-1));
    assert(!Verify(good,server_pub,expected,grant.expires_unix_ms));
    assert(!Verify(good,server_pub,expected,grant.issued_unix_ms-5001));
    assert(Verify(good,server_pub,expected,grant.issued_unix_ms-5000));
    assert(!Verify(good,server_pub,expected,0));

    PubKey fake_pub{};
    SecretKey fake_sec{};
    std::array<u8,32> fake_seed{};
    fake_seed.fill(49);
    LinkMonocypher::crypto_eddsa_key_pair(
        fake_sec.data(),fake_pub.data(),fake_seed.data());
    assert(!Verify(good,fake_pub,expected,grant.issued_unix_ms));
    auto unauthorized=Sign(grant,fake_sec);
    assert(unauthorized);
    assert(!Verify(*unauthorized,server_pub,expected,grant.issued_unix_ms));
    const auto now=grant.issued_unix_ms;
    auto mutated=good;
    mutated.signature[31]^=1;
    assert(!Verify(mutated,server_pub,expected,now));

    // Every security-relevant field is covered by server signature.
    mutated=good;mutated.scope.team="forged-team";
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.party="world:else";
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.sender="hunter-X";
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.receiver="hunter-X";
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.sender_instance++;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.receiver_instance++;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.map++;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.world_epoch++;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.expires_unix_ms+=100;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.sender_ip_nbo^=1;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.receiver_port_nbo^=1;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.responder_noise_pub[0]^=1;
    assert(!Verify(mutated,server_pub,expected,now));
    mutated=good;mutated.scope.grant_nonce[0]^=1;
    assert(!Verify(mutated,server_pub,expected,now));

    // Exact pair is required even when an unexpired signature is valid.
    Expect stale=expected;stale.world_epoch++;
    assert(!Verify(good,server_pub,stale,now));
    stale=expected;stale.party="world:new";
    assert(!Verify(good,server_pub,stale,now));
    stale=expected;stale.sender_instance++;
    assert(!Verify(good,server_pub,stale,now));
    stale=expected;stale.receiver="hunter-C";
    assert(!Verify(good,server_pub,stale,now));
    stale=expected;stale.map++;
    assert(!Verify(good,server_pub,stale,now));

    mutated=good;mutated.scope.sender=mutated.scope.receiver;
    assert(!Valid(mutated.scope));
    assert(!Sign(mutated.scope,server_secret));
    mutated=good;mutated.scope.expires_unix_ms=grant.issued_unix_ms+30001;
    assert(!Sign(mutated.scope,server_secret));
    mutated=good;mutated.scope.team+=std::string(90,'x');
    assert(!Sign(mutated.scope,server_secret));
    mutated=good;mutated.scope.grant_nonce.fill(0);
    assert(!Sign(mutated.scope,server_secret));
    mutated=good;mutated.scope.sender_port_nbo=0;
    assert(!Sign(mutated.scope,server_secret));
    mutated=good;mutated.scope.responder_noise_pub.fill(0);
    assert(!Sign(mutated.scope,server_secret));

    std::puts("SHYT_V279_ORIGINAL_YT_SIGNED_PEER_GRANT_EDDSA_PASS");
}
