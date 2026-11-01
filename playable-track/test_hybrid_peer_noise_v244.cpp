// SPDX-License-Identifier: GPL-2.0-or-later
// Pinned YT original Noise::Symmetric and LinkAuth::Session test vectors.
// The keys here are deterministic synthetic fixtures, NOT deployable secrets.
#include "hybrid_peer_noise_v244.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;
using namespace BloodborneCoop::SHYTHybrid::PeerNoiseV244;

static PeerCryptoScopeV241 scope() {
    return {"party-five-42","hunter-A","hunter-B",17,29,42,0x101};
}
static Key filled(u8 first) {
    Key secret{};
    for(size_t i=0;i<secret.size();i++)
        secret[i]=static_cast<u8>(first+i);
    return secret;
}
static GameFrame movement() {
    GameFrame f{};
    f.sender="hunter-A";f.instance=17;f.peer_instance=29;
    f.entries.push_back({PacketClass::Unreliable,1,
        std::vector<u8>{6,0,0,0,1,0,0,0,42}});
    return f;
}
int main() {
    const Key static_secret=filled(17);
    const Key server_approved_pub=LinkAuth::Noise::PublicOf(static_secret);
    const Key a_secret=filled(55), b_secret=filled(97);
    Initiator alice(scope(),server_approved_pub);
    Responder bob(scope(),static_secret);
    const auto hello=alice.Start(a_secret);
    assert(hello && hello->size()==WireBytes && Prefix(*hello));
    assert(!alice.Start(a_secret)); // ephemeral must not be reused
    const auto answer=bob.Answer(*hello,b_secret);
    assert(answer && answer->answer.size()==WireBytes);
    assert(!bob.Answer(*hello,b_secret)); // one-time state
    const auto client_keys=alice.Finish(answer->answer);
    assert(client_keys && *client_keys==answer->keys);
    assert(!alice.Finish(answer->answer)); // no second key derivation
    assert(client_keys->first!=client_keys->second);

    // Actual original YT AEAD session with the handshake-derived keys.
    PeerCryptoDatagramsV241 sender(scope(),true,
                                  client_keys->first,client_keys->second);
    PeerCryptoDatagramsV241 receiver(scope(),false,
                                  answer->keys.second,answer->keys.first);
    auto sealed=sender.SealMovement(movement());
    assert(sealed);
    assert(receiver.OpenMovement(*sealed)==movement());
    assert(!receiver.OpenMovement(*sealed)); // real replay window

    // Session-id, epoch and correct server-pinned responder key matter.
    auto wrong_scope=scope();wrong_scope.world_epoch++;
    Initiator wrong_epoch(wrong_scope,server_approved_pub);
    assert(!wrong_epoch.Finish(answer->answer));
    const auto wrong_hello=wrong_epoch.Start(filled(111));
    Responder original_scope(scope(),static_secret);
    assert(wrong_hello && !original_scope.Answer(*wrong_hello,filled(113)));
    auto wrong_party=scope();wrong_party.party_session="another-party";
    Responder foreign_party(wrong_party,static_secret);
    assert(!foreign_party.Answer(*hello,filled(117)));
    Initiator wrong_pub(scope(),LinkAuth::Noise::PublicOf(filled(121)));
    const auto stranger=wrong_pub.Start(filled(125));
    Responder pinned(scope(),static_secret);
    assert(stranger && !pinned.Answer(*stranger,filled(129)));

    // Reject mutated handshake messages (AEAD tag and scope).
    auto tampered=*hello;
    tampered.back()^=0x01;
    Responder checked(scope(),static_secret);
    assert(!checked.Answer(tampered,filled(137)));
    tampered=*hello;
    tampered[4]=2; // protocol version
    Responder unknown(scope(),static_secret);
    assert(!unknown.Answer(tampered,filled(139)));
    tampered=*hello;
    tampered.resize(tampered.size()-3);
    Responder truncated(scope(),static_secret);
    assert(!truncated.Answer(tampered,filled(141)));

    // A damaged answer must be ignored, leaving the pending initiator
    // handshake usable when the genuine response arrives afterwards.
    Initiator retry(scope(),server_approved_pub);
    Responder retry_peer(scope(),static_secret);
    auto retry_hello=retry.Start(filled(143));
    assert(retry_hello);
    const auto retry_answer=retry_peer.Answer(*retry_hello,filled(157));
    assert(retry_answer);
    auto broken=retry_answer->answer;
    broken.back()^=0x80;
    assert(!retry.Finish(broken));
    assert(retry.Finish(retry_answer->answer));

    puts("SHYT_V244_PINNED_YT_NOISE_NK_PEER_HANDSHAKE_SYNTHETIC_PASS");
}
