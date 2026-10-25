// SPDX-License-Identifier: GPL-2.0-or-later
// V82 portable recipient of the ACTUAL V75 SHG1 wire from V81 TLS.
#include "sh_native_grant_inbox.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static constexpr std::uint64_t kSelf=1201,kPeer=2202,kEpoch=303,kWorld=404;
struct GameState {
    bool available=true;
    NativeOfferIdentity identity{kSelf,kPeer,kEpoch,kWorld,true};
};
static bool Current(NativeOfferIdentity& out,void* ctx) noexcept {
    const auto& s=*static_cast<GameState*>(ctx);
    if(!s.available)return false;
    out=s.identity;return true;
}
static std::array<std::uint8_t,32> Key(int offset=0) {
    std::array<std::uint8_t,32> k{};
    for(unsigned i=0;i<k.size();++i)
        k[i]=static_cast<std::uint8_t>(i+offset+11);
    return k;
}
static SecurePeerOffer PeerOffer() {
    SecurePeerOffer p{};
    p.sender_account=kPeer;p.recipient_account=kSelf;
    p.session_epoch=kEpoch;p.pair_binding=505;p.world_revision=kWorld;
    p.issued_ms=1000;p.expires_ms=2000;
    p.peer_ipv4_nbo=0x01020304;p.peer_port_nbo=0x3412;
    p.peer_virtual_ipv4_nbo=0x05060708;p.peer_virtual_port_nbo=0x1122;
    p.direction_key=Key(50);
    return p;
}
static std::string Hex(std::span<const std::uint8_t> bytes) {
    static constexpr char hex[]="0123456789abcdef";
    std::string out;out.reserve(bytes.size()*2);
    for(std::uint8_t b:bytes){out.push_back(hex[b>>4]);out.push_back(hex[b&15]);}
    return out;
}
static std::string Line(SecurePeerOffer p,std::span<const std::uint8_t> key) {
    SealedPeerOffers srv;assert(srv.InstallChannelKey(key));
    std::vector<std::uint8_t> encrypted;
    assert(srv.Seal(p,1001,encrypted));
    assert(encrypted.size()==NativeSealedGrantInbox::kCipherBytes);
    auto line=std::string(NativeSealedGrantInbox::kPrefix)+Hex(encrypted)+"\n";
    assert(line.size()==NativeSealedGrantInbox::kLineBytes);
    CryptoDetail::Erase(p.direction_key);
    CryptoDetail::Erase(encrypted);
    return line;
}
int main() {
    const auto key=Key();
    const auto offer=PeerOffer();
    auto line=Line(offer,key);
    NativeSealedGrantInbox inbox;
    GameState world{};
    assert(!inbox.BeginTrustedTls({},world.identity,1,Current,&world));
    assert(!inbox.BeginTrustedTls(key,{},1,Current,&world));
    assert(!inbox.BeginTrustedTls(key,world.identity,0,Current,&world));
    assert(!inbox.BeginTrustedTls(key,world.identity,1,nullptr,&world));
    assert(!inbox.BeginTrustedTls(key,world.identity,1,Current,nullptr));
    assert(inbox.BeginTrustedTls(key,world.identity,1,Current,&world));
    assert(inbox.ReceiveSealedTlsLine(line,1100));
    assert(inbox.IsPending());
    const auto* staged=inbox.PendingForNat(1100);
    assert(staged);
    assert(staged->sender_account==kPeer);
    assert(staged->recipient_account==kSelf);
    assert(staged->session_epoch==kEpoch);
    assert(staged->world_revision==kWorld);
    assert(staged->peer_ipv4_nbo==offer.peer_ipv4_nbo);
    assert(staged->peer_port_nbo==offer.peer_port_nbo);
    assert(staged->peer_virtual_ipv4_nbo==offer.peer_virtual_ipv4_nbo);
    assert(staged->peer_virtual_port_nbo==offer.peer_virtual_port_nbo);
    assert(staged->direction_key==offer.direction_key);
    // Failure of a duplicated offer burns the session and clears secret.
    assert(!inbox.ReceiveSealedTlsLine(line,1100));
    assert(!inbox.IsPending());
    assert(inbox.PendingForNat(1100)==nullptr);
    assert(!inbox.BeginTrustedTls(key,world.identity,1,Current,&world));
    assert(inbox.BeginTrustedTls(key,world.identity,2,Current,&world));
    assert(inbox.ReceiveSealedTlsLine(line,1100));
    world.identity.world_revision=kWorld+1;
    assert(!inbox.HasCurrentPending(1100));
    assert(!inbox.IsPending());
    world.identity.world_revision=kWorld;
    assert(inbox.BeginTrustedTls(key,world.identity,3,Current,&world));
    assert(inbox.ReceiveSealedTlsLine(line,1100));
    world.identity.locally_opted_in=false;
    assert(!inbox.HasCurrentPending(1100));
    world.identity.locally_opted_in=true;
    assert(inbox.BeginTrustedTls(key,world.identity,4,Current,&world));
    assert(inbox.ReceiveSealedTlsLine(line,1100));
    assert(!inbox.HasCurrentPending(2000)); // exact expiration
    assert(inbox.BeginTrustedTls(key,world.identity,5,Current,&world));
    auto mutated=line;mutated[30]=(mutated[30]=='0'?'1':'0');
    assert(!inbox.ReceiveSealedTlsLine(mutated,1100));
    assert(inbox.BeginTrustedTls(key,world.identity,6,Current,&world));
    mutated=line;mutated[NativeSealedGrantInbox::kPrefix.size()]='G';
    assert(!inbox.ReceiveSealedTlsLine(mutated,1100));
    assert(inbox.BeginTrustedTls(key,world.identity,7,Current,&world));
    mutated=line;mutated[0]='X';
    assert(!inbox.ReceiveSealedTlsLine(mutated,1100));
    assert(inbox.BeginTrustedTls(key,world.identity,8,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(std::string_view(line).substr(0,line.size()-1),1100));
    assert(inbox.BeginTrustedTls(key,world.identity,9,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(line,999));
    assert(inbox.BeginTrustedTls(Key(3),world.identity,10,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(line,1100));
    auto wrong_sender=offer;wrong_sender.sender_account=5555;
    assert(inbox.BeginTrustedTls(key,world.identity,11,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(Line(wrong_sender,key),1100));
    auto wrong_recipient=offer;wrong_recipient.recipient_account=5555;
    assert(inbox.BeginTrustedTls(key,world.identity,12,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(Line(wrong_recipient,key),1100));
    auto wrong_world=offer;wrong_world.world_revision=kWorld+1;
    assert(inbox.BeginTrustedTls(key,world.identity,13,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(Line(wrong_world,key),1100));
    auto wrong_epoch=offer;wrong_epoch.session_epoch=kEpoch+1;
    assert(inbox.BeginTrustedTls(key,world.identity,14,Current,&world));
    assert(!inbox.ReceiveSealedTlsLine(Line(wrong_epoch,key),1100));
    world.available=false;
    assert(!inbox.BeginTrustedTls(key,world.identity,15,Current,&world));
    world.available=true;
    assert(inbox.BeginTrustedTls(key,world.identity,15,Current,&world));
    assert(inbox.ReceiveSealedTlsLine(line,1100));
    world.available=false;
    assert(inbox.PendingForNat(1100)==nullptr);
    inbox.Revoke();
    assert(!inbox.IsPending());
    return 0;
}
