// SPDX-License-Identifier: GPL-2.0-or-later
// Synthetic private-key fixtures, original YT 1.3.1 GameFrame/LinkAuth crypto.
#include "hybrid_peer_crypto_v241.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;

static PeerCryptoScopeV241 scope() {
    return {"five-team-42","hunter-A","hunter-B",17,29,42,0x101};
}
static GameFrame player_state(u32 seq=1) {
    GameFrame f{};
    f.sender="hunter-A"; f.instance=17; f.peer_instance=29;
    f.entries.push_back({PacketClass::Unreliable,seq,
                         std::vector<u8>{6,0,0,0, 1,0,0,0,42}});
    return f;
}
int main() {
    LinkAuth::Key ab{},ba{};
    for (size_t i=0;i<ab.size();i++) {
        ab[i]=static_cast<u8>(i+1);
        ba[i]=static_cast<u8>(255-i);
    }
    PeerCryptoDatagramsV241 alice(scope(),true,ab,ba);
    PeerCryptoDatagramsV241 bob(scope(),false,ba,ab);
    const auto plain=player_state();
    auto wire=alice.SealMovement(plain);
    assert(wire && wire->size()<PeerCryptoDatagramsV241::MaxDatagram);
    assert(wire->size()>EncodeGameFrame(plain).size());
    assert((*wire)[4]=='S' && (*wire)[5]=='H' && (*wire)[6]=='D');
    auto decoded=bob.OpenMovement(*wire);
    assert(decoded && *decoded==plain);
    assert(!bob.OpenMovement(*wire)); // replay with same authenticated counter
    auto second=alice.SealMovement(player_state(2));
    assert(second);
    auto damaged=*second;
    damaged[damaged.size()-1]^=0x40; // authenticate tag
    assert(!bob.OpenMovement(damaged));
    assert(bob.OpenMovement(*second)); // failed tag must not consume counter
    auto cropped=*wire;
    cropped.resize(10);
    assert(!bob.OpenMovement(cropped));

    // Different party/world epoch cannot borrow a valid encrypted packet,
    // even if an external key exchange mistakenly reused directional keys.
    auto different=scope();different.world_epoch=99;
    PeerCryptoDatagramsV241 wrong_world(different,false,ba,ab);
    auto third=alice.SealMovement(player_state(3));
    assert(third && !wrong_world.OpenMovement(*third));
    different=scope();different.party_session="other-team";
    PeerCryptoDatagramsV241 wrong_party(different,false,ba,ab);
    assert(!wrong_party.OpenMovement(*third));
    LinkAuth::Key another=ba;another[0]^=0x55;
    PeerCryptoDatagramsV241 wrong_key(scope(),false,ba,another);
    assert(!wrong_key.OpenMovement(*third));

    auto invalid=plain; invalid.sender="hunter-C";
    assert(!alice.SealMovement(invalid));
    invalid=plain;invalid.ack=1;
    assert(!alice.SealMovement(invalid)); // reliable ACK must stay on server
    invalid=plain;invalid.entries[0].packet[0]=5;
    assert(!alice.SealMovement(invalid)); // enemy HP not eligible
    invalid=plain;invalid.entries[0].packet[4]=100;
    assert(!alice.SealMovement(invalid)); // bad native frame length
    invalid=plain;invalid.entries[0].packet_class=PacketClass::Reliable;
    assert(!alice.SealMovement(invalid));

    // Zero-length names / epoch are rejected; equal directional keys
    // are not accepted by the paired-session object.
    auto empty=scope();empty.party_session.clear();
    PeerCryptoDatagramsV241 bad_scope(empty,true,ab,ba);
    assert(!bad_scope.SealMovement(plain));
    PeerCryptoDatagramsV241 bad_keys(scope(),true,ab,ab);
    assert(!bad_keys.SealMovement(plain));

    // Session replay guard survives opposite-direction ACK-free traffic.
    GameFrame reply{};
    reply.sender="hunter-B"; reply.instance=29;reply.peer_instance=17;
    reply.entries.push_back({PacketClass::Unreliable,1,
                              std::vector<u8>{6,0,0,0,1,0,0,0,43}});
    auto back=bob.SealMovement(reply);
    assert(back);
    assert(alice.OpenMovement(*back)==reply);
    assert(!alice.OpenMovement(*back));
    puts("SHYT_V241_ORIGINAL_LINKAUTH_PEER_CRYPTO_SYNTHETIC_PASS");
}
