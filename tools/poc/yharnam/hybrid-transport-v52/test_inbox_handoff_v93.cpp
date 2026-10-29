// SPDX-License-Identifier: GPL-2.0-or-later
// V93 detached TLS worker inbox -> short locked original game handoff.
// Independent pure C++20 OpenSSL and Windows CNG test; no game UDP routing.
#include "sh_native_grant_inbox_v84.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> Id(std::uint8_t first) {
    std::array<std::uint8_t,32> out{};
    for(unsigned i=0;i<32;++i)out[i]=static_cast<std::uint8_t>(first+i);
    return out;
}
struct Live {
    NativeOfferIdentityV84 identity{Id(1),Id(71),31,91,true};
    bool consent=true;
};
static bool Refresh(NativeOfferIdentityV84& dst,void* opaque) noexcept {
    const auto& state=*static_cast<Live*>(opaque);
    if(!state.consent)return false;
    dst=state.identity;return true;
}
static std::string Line(const SecurePeerOfferV84& grant,
                        const std::array<std::uint8_t,32>& wrapping) {
    SealedPeerOffersV84 sealer{};
    assert(sealer.InstallChannelKey(wrapping));
    std::vector<std::uint8_t> cipher;
    assert(sealer.Seal(grant,1001,cipher));
    static constexpr char hex[]="0123456789abcdef";
    std::string message(NativeSealedGrantInboxV84::kPrefix);
    for(const auto b:cipher) {
        message.push_back(hex[b>>4]);
        message.push_back(hex[b&15]);
    }
    message.push_back('\n');
    assert(message.size()==NativeSealedGrantInboxV84::kLineBytes);
    CryptoDetail::Erase(cipher);
    return message;
}
int main() {
    Live world{};
    const auto key=Id(121);
    SecurePeerOfferV84 offer{};
    offer.recipient_account=world.identity.self_account;
    offer.sender_account=world.identity.peer_account;
    offer.session_epoch=world.identity.session_epoch;
    offer.world_revision=world.identity.world_revision;
    offer.pair_binding=1234567;
    offer.issued_ms=1000;offer.expires_ms=2000;
    offer.peer_ipv4_nbo=0x01020304;offer.peer_port_nbo=40111;
    offer.peer_virtual_ipv4_nbo=0x0a010203;offer.peer_virtual_port_nbo=31214;
    offer.direction_key=Id(181);
    const auto line=Line(offer,key);
    NativeSealedGrantInboxV84 game;
    NativeSealedGrantInboxV84 worker;
    assert(worker.BeginTrustedTls(key,world.identity,1,Refresh,&world));
    assert(worker.ReceiveSealedTlsLine(line,1100));
    assert(worker.TransferVerifiedTo(game,1100));
    assert(!worker.IsPending() && game.IsPending());
    assert(game.PendingForNat(1100)->direction_key==offer.direction_key);
    assert(!worker.TransferVerifiedTo(game,1100));
    game.Revoke();
    assert(game.PendingForNat(1100)==nullptr);
    assert(worker.BeginTrustedTls(key,world.identity,2,Refresh,&world));
    assert(worker.ReceiveSealedTlsLine(line,1100));
    assert(worker.TransferVerifiedTo(game,1100));
    assert(game.IsPending());
    // A new worker with reused TLS serial MUST NOT replace the game
    // inbox. Preserve the existing current game grant on failed handoff.
    NativeSealedGrantInboxV84 replay;
    assert(replay.BeginTrustedTls(key,world.identity,2,Refresh,&world));
    assert(replay.ReceiveSealedTlsLine(line,1100));
    assert(!replay.TransferVerifiedTo(game,1100));
    assert(game.PendingForNat(1100)!=nullptr);
    // Consent and world mutation during asynchronous TLS immediately
    // prohibit publication, zeroing both temporary and game grant.
    game.Revoke();
    world.consent=false;
    assert(!replay.TransferVerifiedTo(game,1100));
    assert(!game.IsPending());
    world.consent=true;
    assert(worker.BeginTrustedTls(key,world.identity,3,Refresh,&world));
    assert(worker.ReceiveSealedTlsLine(line,1100));
    world.identity.world_revision++;
    assert(!worker.TransferVerifiedTo(game,1100));
    assert(!game.IsPending());
    world.identity.world_revision--;
    assert(worker.BeginTrustedTls(key,world.identity,4,Refresh,&world));
    assert(worker.ReceiveSealedTlsLine(line,1100));
    assert(!worker.TransferVerifiedTo(game,2000)); // expired before publish
    assert(!game.IsPending());
    // No shallow pointer transfer: callback remains the trusted game's
    // original state, so a later revoke invalidates the new owner.
    assert(worker.BeginTrustedTls(key,world.identity,5,Refresh,&world));
    assert(worker.ReceiveSealedTlsLine(line,1100));
    assert(worker.TransferVerifiedTo(game,1100));
    world.consent=false;
    assert(game.PendingForNat(1101)==nullptr);
    assert(!game.IsPending());
    return 0;
}
