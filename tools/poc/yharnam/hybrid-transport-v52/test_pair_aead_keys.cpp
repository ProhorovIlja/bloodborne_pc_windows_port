// SPDX-License-Identifier: GPL-2.0-or-later
// Two real C++ directional key schedules from the SAME SHG2 pair master.
// Verifies A-outgoing == B-incoming and a ciphertext from one direction
// cannot be decrypted in the opposite direction or another world/pair.
#include "sh_pair_aead_keys.hpp"
#include "sh_native_game_aead.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> Id(unsigned start) {
    std::array<std::uint8_t,32> id{};
    for(std::size_t i=0;i<id.size();++i)
        id[i]=static_cast<std::uint8_t>(start+i);
    return id;
}
static SecurePeerOfferV84 OfferA() {
    SecurePeerOfferV84 offer{};
    offer.sender_account=Id(5); // peer B
    offer.recipient_account=Id(60); // self A
    offer.session_epoch=77; // LOCAL A epoch, need not equal B
    offer.pair_binding=414243;
    offer.world_revision=919293;
    offer.issued_ms=1000;
    offer.expires_ms=2000;
    offer.peer_ipv4_nbo=0x04030201;
    offer.peer_port_nbo=44123;
    offer.peer_virtual_ipv4_nbo=0x0403020a;
    offer.peer_virtual_port_nbo=31314;
    offer.direction_key=Id(101); // shared pair master, mTLS-wrapped separately
    return offer;
}
static PeerTicket TrustedSameDirectionTicket(const SecurePeerOfferV84& offer) {
    PeerTicket t{};
    // Common wire generation must be agreed by BOTH members of the pair.
    // Local recipient session epochs differ; the authenticated world
    // revision + pair binding come from the same server-coordinated pair.
    t.session_epoch=offer.world_revision;
    t.pair_binding=offer.pair_binding;
    t.authenticated_sender=111; // synthetic test only, never from UDP
    t.local_receiver=222;
    t.expires_at_ms=static_cast<std::int64_t>(offer.expires_ms);
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
int main(){
    const auto a=OfferA();
    auto b=a;
    b.sender_account=a.recipient_account;
    b.recipient_account=a.sender_account;
    b.session_epoch=88; // DIFFERENT local sign-in generation
    NativePairAeadMaterial a_out,b_in,a_in,b_out;
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(a,true,1001,a_out));
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(b,false,1001,b_in));
    assert(a_out.key==b_in.key);
    assert(a_out.salt==b_in.salt);
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(a,false,1001,a_in));
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(b,true,1001,b_out));
    assert(a_in.key==b_out.key && a_in.salt==b_out.salt);
    assert(a_out.key!=a_in.key && a_out.salt!=a_in.salt);
    assert(a_out.key!=a.direction_key);
    NativeGameAeadSealer game_from_a;
    NativeGameAeadOpener game_at_b;
    const auto direction=TrustedSameDirectionTicket(a);
    assert(game_from_a.Arm(direction,a_out.key,a_out.salt,1001));
    assert(game_at_b.Arm(direction,b_in.key,b_in.salt,1001));
    const std::vector<std::uint8_t> payload{0xff,0xff,'S','H','A','D','A','E','S'};
    std::vector<std::uint8_t> cipher,plain;
    assert(game_from_a.SealGame(payload,1002,cipher));
    assert(game_at_b.OpenGame(cipher,1002,plain) && plain==payload);
    assert(!game_at_b.OpenGame(cipher,1003,plain)); // replay
    // A's game Data must not be readable with B->A key or another pair.
    NativeGameAeadOpener wrong_direction;
    assert(wrong_direction.Arm(direction,a_in.key,a_in.salt,1001));
    assert(!wrong_direction.OpenGame(cipher,1002,plain));
    auto different=b;different.world_revision++;
    NativePairAeadMaterial wrong_world;
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(
           different,false,1001,wrong_world));
    assert(wrong_world.key!=a_out.key);
    auto different_pair=b;different_pair.pair_binding++;
    NativePairAeadMaterial wrong_pair;
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(
           different_pair,false,1001,wrong_pair));
    assert(wrong_pair.key!=a_out.key);
    auto forged=b;forged.direction_key.fill(0);
    NativePairAeadMaterial blocked;
    assert(!NativePairAeadKeys::DeriveFromVerifiedInbox(forged,false,1001,blocked));
    assert(std::all_of(blocked.key.begin(),blocked.key.end(),[](auto x){return x==0;}));
    assert(!NativePairAeadKeys::DeriveFromVerifiedInbox(b,false,2000,blocked));
    assert(NativePairAeadKeys::DeriveFromVerifiedInbox(b,false,1001,blocked));
    assert(blocked.key==a_out.key && blocked.salt==a_out.salt);
    return 0;
}
