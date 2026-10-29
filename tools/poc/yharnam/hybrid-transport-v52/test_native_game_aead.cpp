// SPDX-License-Identifier: GPL-2.0-or-later
// Tests confidentiality and replay protection only. A real server-controlled
// peer handshake and live P2PTransport activation are not simulated here.
#include "sh_native_game_aead.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static PeerTicket Ticket() {
    PeerTicket t{};
    t.session_epoch=77;t.pair_binding=998;
    t.authenticated_sender=10;t.local_receiver=11;t.expires_at_ms=20000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static std::array<std::uint8_t,32> Key(std::uint8_t n) {
    std::array<std::uint8_t,32> result{};
    for(std::size_t i=0;i<result.size();++i)
        result[i]=static_cast<std::uint8_t>(n+i);
    return result;
}
static std::array<std::uint8_t,4> Salt(std::uint8_t n) {
    return {n,static_cast<std::uint8_t>(n+1),
            static_cast<std::uint8_t>(n+2),
            static_cast<std::uint8_t>(n+3)};
}
static std::vector<std::uint8_t> Game() {
    return {0xff,0xff,0xff,0xff,'S','H','A','D',
            'H','u','n','t','e','r','s',' ','t','o','g','e','t','h','e','r'};
}
int main(){
    const auto key=Key(10);
    const auto salt=Salt(40);
    const auto game=Game();
    const auto ticket=Ticket();
    NativeGameAeadSealer tx;
    NativeGameAeadOpener rx;
    std::vector<std::uint8_t> out,original,plain;
    assert(!tx.SealGame(game,101,out));
    assert(!rx.OpenGame(game,101,plain));
    auto revoked=ticket;revoked.both_consented=false;
    assert(!tx.Arm(revoked,key,salt,100));
    assert(!rx.Arm(revoked,key,salt,100));
    assert(tx.Arm(ticket,key,salt,100));
    assert(rx.Arm(ticket,key,salt,100));
    // A second Arm cannot silently reset the nonce/replay sequence.
    assert(!tx.Arm(ticket,key,salt,100));
    assert(!rx.Arm(ticket,key,salt,100));
    assert(tx.SealGame(game,101,out));
    original=out;
    assert(out.size()==AeadDetail::HeaderBytes+game.size()+AeadDetail::TagBytes);
    assert(std::search(out.begin(),out.end(),game.begin(),game.end())==out.end());
    assert(rx.OpenGame(out,101,plain) && plain==game);
    assert(!rx.OpenGame(out,101,plain) && plain.empty()); // replay
    // Header is authenticated and bound to both server-issued epoch and pair.
    for(std::size_t flip:{std::size_t{0},std::size_t{4},std::size_t{8},
                          std::size_t{16},std::size_t{24},
                          AeadDetail::HeaderBytes,
                          out.size()-1}) {
        auto corrupted=original;
        corrupted[flip]^=0x80;
        assert(!rx.OpenGame(corrupted,102,plain));
        assert(plain.empty()); // decrypt must not emit unauthenticated data
    }
    // A bad tag never advances the replay window: this is a NEW seq.
    std::vector<std::uint8_t> two,three,four;
    assert(tx.SealGame(game,102,two));
    auto wrong=two;wrong.back()^=0x01;
    assert(!rx.OpenGame(wrong,102,plain) && plain.empty());
    assert(tx.SealGame(game,103,three));
    assert(tx.SealGame(game,104,four));
    assert(rx.OpenGame(four,104,plain) && plain==game);
    assert(rx.OpenGame(two,105,plain) && plain==game);
    assert(rx.OpenGame(three,106,plain) && plain==game);
    assert(!rx.OpenGame(two,107,plain));
    // Another encryption key, nonce salt or pairing must fail authentication.
    NativeGameAeadOpener wrong_key,wrong_salt,wrong_pair;
    assert(wrong_key.Arm(ticket,Key(30),salt,100));
    assert(wrong_salt.Arm(ticket,key,Salt(50),100));
    auto pairing=ticket;pairing.pair_binding++;
    assert(wrong_pair.Arm(pairing,key,salt,100));
    assert(!wrong_key.OpenGame(two,105,plain));
    assert(!wrong_salt.OpenGame(two,105,plain));
    assert(!wrong_pair.OpenGame(two,105,plain));
    // Out-of-window replay: no MAC work and no packet delivered.
    for(int i=0;i<70;++i){
        std::vector<std::uint8_t> packet;
        assert(tx.SealGame(game,200+i,packet));
        assert(rx.OpenGame(packet,200+i,plain) && plain==game);
    }
    assert(!rx.OpenGame(original,300,plain) && plain.empty());
    std::vector<std::uint8_t> oversized(AeadDetail::MaxPayload+1,0x11);
    assert(!tx.SealGame(oversized,300,out) && out.empty());
    assert(!tx.SealGame(game,20001,out));
    assert(!rx.OpenGame(four,20001,plain) && plain.empty());
    tx.Revoke();rx.Revoke();
    assert(!tx.SealGame(game,100,out));
    assert(!rx.OpenGame(four,100,plain));
    // Ciphertext from a previous server epoch cannot cross into a new one.
    auto next=ticket;next.session_epoch++;
    assert(tx.Arm(next,Key(91),Salt(91),100));
    assert(rx.Arm(next,Key(91),Salt(91),100));
    assert(!rx.OpenGame(original,101,plain));
    assert(tx.SealGame(game,102,out));
    assert(rx.OpenGame(out,102,plain) && plain==game);
    // Empty/zero key/salt or sender==receiver are refused.
    NativeGameAeadSealer invalid;
    std::array<std::uint8_t,32> zeros{};
    std::array<std::uint8_t,4> empty_salt{};
    assert(!invalid.Arm(ticket,zeros,salt,100));
    assert(!invalid.Arm(ticket,key,empty_salt,100));
    next.local_receiver=next.authenticated_sender;
    assert(!invalid.Arm(next,key,salt,100));
    return 0;
}
