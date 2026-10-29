// SPDX-License-Identifier: GPL-2.0-or-later
// V103: one actual native hunter may hold FOUR independent server-sealed
// pending SHG2 offers. Tests secrets, overflow, relink, role/epoch changes.
// No game UDP Direct is enabled by these grants.
#include "sh_native_team_grant_slots_v103.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>

using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> Id(unsigned seed) {
    std::array<std::uint8_t,32> result{};
    for(unsigned i=0;i<32;++i)
        result[i]=static_cast<std::uint8_t>(seed+i);
    return result;
}
struct LiveGame {
    NativeOfferIdentityV84 identity{};
    bool consent=true;
};
static bool Refresh(NativeOfferIdentityV84& out,void* state) noexcept {
    const auto& live=*static_cast<LiveGame*>(state);
    if(!live.consent)return false;
    out=live.identity;return true;
}
static std::string Sealed(const SecurePeerOfferV84& offer,
                          std::span<const std::uint8_t> wrapper) {
    SealedPeerOffersV84 cipher{};
    assert(cipher.InstallChannelKey(wrapper));
    std::vector<std::uint8_t> encrypted;
    assert(cipher.Seal(offer,1001,encrypted));
    constexpr char hex[]="0123456789abcdef";
    std::string reply(NativeSealedGrantInboxV84::kPrefix);
    for(const auto c:encrypted) {
        reply.push_back(hex[c>>4]);
        reply.push_back(hex[c&15]);
    }
    reply.push_back('\n');
    assert(reply.size()==NativeSealedGrantInboxV84::kLineBytes);
    CryptoDetail::Erase(encrypted);
    return reply;
}
static bool Issue(NativeTeamGrantSlotsV103& slots,LiveGame& state,
                  std::uint64_t pair_id,std::uint64_t selected_id,
                  std::uint64_t tls_serial=1,
                  std::uint64_t link_generation=44) {
    auto& identity=state.identity;
    SecurePeerOfferV84 offer{};
    offer.recipient_account=identity.self_account;
    offer.sender_account=identity.peer_account;
    offer.session_epoch=identity.session_epoch;
    offer.world_revision=identity.world_revision;
    offer.pair_binding=pair_id;
    offer.issued_ms=1000;offer.expires_ms=2000;
    offer.peer_ipv4_nbo=0x01020304;
    offer.peer_port_nbo=40111;
    offer.peer_virtual_ipv4_nbo=0x0a010203;
    offer.peer_virtual_port_nbo=31214;
    offer.direction_key=Id(static_cast<unsigned>(pair_id));
    const auto wrapper=Id(17);
    NativeSealedGrantInboxV84 worker;
    assert(worker.BeginTrustedTls(wrapper,identity,tls_serial,Refresh,&state));
    const auto line=Sealed(offer,wrapper);
    assert(worker.ReceiveSealedTlsLine(line,1100));
    const bool accepted=slots.InstallVerified(
        worker,selected_id,link_generation,1100);
    assert(worker.IsPending()!=accepted); // transfer only on success
    CryptoDetail::Erase(offer.direction_key);
    return accepted;
}
int main() {
    NativeTeamGrantSlotsV103 slots;
    assert(slots.Count()==0);
    std::array<LiveGame,5> members{};
    for(unsigned i=0;i<members.size();++i)
        members[i].identity={
            Id(1),Id(81+i),31,91,true};
    for(unsigned i=0;i<4;++i)
        assert(Issue(slots,members[i],100+i,100+i));
    assert(slots.Count()==4);
    for(unsigned i=0;i<4;++i) {
        const auto* grant=slots.PendingForNat(100+i,44,1101);
        assert(grant && grant->pair_binding==100+i);
        assert(grant->sender_account==members[i].identity.peer_account);
    }
    assert(!slots.PendingForNat(100,45,1101)); // stale link generation
    assert(slots.Count()==4); // must not erase valid current generation
    assert(!Issue(slots,members[0],100,100,2)); // duplicate selector
    assert(!Issue(slots,members[4],104,104)); // no unbounded fifth slot
    assert(!Issue(slots,members[4],104,999)); // wrong server selector
    assert(slots.Count()==4);
    assert(!slots.RevokePair(999));
    assert(slots.RevokePair(101));
    assert(slots.Count()==3);
    assert(!slots.PendingForNat(101,44,1101));
    assert(Issue(slots,members[4],104,104,2));
    assert(slots.Count()==4);
    assert(slots.PendingForNat(104,44,1101));
    assert(slots.PendingForNat(100,44,1101));
    // An independent guest revokes its consent: no other pair is lost.
    members[2].consent=false;
    assert(!slots.PendingForNat(102,44,1102));
    assert(slots.Count()==3);
    assert(slots.PendingForNat(100,44,1102));
    assert(slots.PendingForNat(103,44,1102));
    // World/map/epoch transition kills the affected pending authority.
    members[0].identity.world_revision++;
    slots.Sweep(1103);
    assert(slots.Count()==2);
    assert(!slots.PendingForNat(100,44,1103));
    assert(slots.PendingForNat(104,44,1103));
    // All local game-owned secrets are discarded on logout or server relink.
    slots.RevokeAll();
    assert(slots.Count()==0);
    assert(!slots.PendingForNat(104,44,1104));
    assert(Issue(slots,members[4],105,105,3,45));
    assert(slots.Count()==1);
    slots.Sweep(2000); // exclusive expiration
    assert(slots.Count()==0);
    assert(!slots.PendingForNat(105,45,2000));
    return 0;
}
