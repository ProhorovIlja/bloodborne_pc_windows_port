// SPDX-License-Identifier: GPL-2.0-or-later
// Server-owned V90 2-recipient SHG2 mTLS lease. Nothing in game UDP route.
#include "sh_p2p_pair_lease_v90.hpp"
#include "sh_pair_key_schedule_v89.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;

struct Source {
    bool opted=true;
    bool enrolled=true;
    quint64 epoch_a=101,epoch_b=202,world=303;
    quint16 port_a=45551,port_b=45552;
    int reads=0;
    std::optional<P2PLocalOfferScope> Scope(
        const QByteArray& recipient,const QByteArray& peer) {
        ++reads;
        if(!opted || !enrolled)return std::nullopt;
        if(recipient=="A" && peer=="B")
            return P2PLocalOfferScope{"A","B",epoch_a,epoch_b,world,
                                     0x7f000001u,port_b,0x0a010002u,1112};
        if(recipient=="B" && peer=="A")
            return P2PLocalOfferScope{"B","A",epoch_b,epoch_a,world,
                                     0x7f000001u,port_a,0x0a010001u,1111};
        return std::nullopt;
    }
};
static P2PPairLeaseV90::Resolver Resolver(Source& src) {
    return [&](const QByteArray& a,const QByteArray& b) {
        return src.Scope(a,b);
    };
}
int main() {
    Source src{};
    P2PPairLeaseV90 lease;
    SecurePeerOfferV84 a{},b{};
    assert(!lease.Take("A",101,1000,a));
    assert(!lease.Begin("A","A",Resolver(src),1000));
    assert(!lease.Begin("A","B",{},1000));
    assert(!lease.Begin("A","B",Resolver(src),0));
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(src.reads==4); // authoritative double-check at creation
    assert(lease.Active());
    assert(!lease.Take("A",101,999,a)); // request predates issuance
    assert(!lease.Active());            // fails closed, erases both keys
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(!lease.Take("attacker",101,1001,a));
    // A third signed-in account must not be able to DoS a live unrelated
    // two-player pair by invoking the mTLS OFFER handler.
    assert(lease.Active());
    assert(lease.HasOutstanding(1001));
    assert(!lease.Take("attacker",202,1002,a));
    assert(lease.Active());
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(!lease.Take("A",102,1001,a));
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(lease.Take("A",101,1001,a));
    const auto bind=a.pair_binding;
    assert(bind!=0 && a.world_revision==303);
    assert(a.peer_port_nbo==qToBigEndian(quint16(src.port_b)));
    assert(lease.Take("B",202,1002,b));
    assert(a.pair_binding==b.pair_binding);
    assert(a.world_revision==b.world_revision);
    assert(a.direction_key==b.direction_key); // pair master sealed twice
    assert(a.sender_account==b.recipient_account);
    assert(a.recipient_account==b.sender_account);
    std::array<std::uint8_t,32> a_tx{},b_rx{},b_tx{},a_rx{};
    assert(PairKeyScheduleV89::Derive(a,true,PairKeyPurposeV89::NatProbe,1002,a_tx));
    assert(PairKeyScheduleV89::Derive(b,false,PairKeyPurposeV89::NatProbe,1002,b_rx));
    assert(PairKeyScheduleV89::Derive(b,true,PairKeyPurposeV89::NatProbe,1002,b_tx));
    assert(PairKeyScheduleV89::Derive(a,false,PairKeyPurposeV89::NatProbe,1002,a_rx));
    assert(a_tx==b_rx && b_tx==a_rx && a_tx!=b_tx);
    PairReadyProofV91::Tag proof_a{},proof_b{};
    bool both_ready=false;
    assert(PairReadyProofV91::Create(a,1002,proof_a));
    assert(PairReadyProofV91::Create(b,1002,proof_b));
    assert(!lease.MarkReady("attacker",101,proof_a,1002,both_ready));
    assert(!both_ready && lease.HasOutstanding(1002));
    assert(!lease.MarkReady("attacker",202,proof_b,1002,both_ready));
    assert(!both_ready && lease.HasOutstanding(1002));
    assert(lease.MarkReady("A",101,proof_a,1002,both_ready));
    assert(!both_ready);
    assert(lease.MarkReady("B",202,proof_b,1003,both_ready));
    assert(both_ready && lease.BothReady(1003));
    assert(!lease.Take("A",101,1003,a)); // no third/replayed ticket
    assert((a.direction_key==std::array<std::uint8_t,32>{}));
    assert(!lease.Active());

    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(lease.Take("A",101,1001,a));
    src.world++;
    assert(!lease.Take("B",202,1002,b));
    assert((b.direction_key==std::array<std::uint8_t,32>{}));
    assert(!lease.Active());src.world--;
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(lease.Take("A",101,1001,a));
    src.epoch_a++;
    assert(!lease.Take("B",202,1002,b));
    assert(!lease.Active());src.epoch_a--;
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(lease.Take("A",101,1001,a));
    src.opted=false;
    assert(!lease.Take("B",202,1002,b));
    assert(!lease.Active());src.opted=true;

    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(lease.Take("A",101,1001,a));
    assert(!lease.Take("B",202,11000,b)); // exactly expired
    assert(!lease.Active());
    assert(lease.Begin("A","B",Resolver(src),1000));
    assert(lease.Take("B",202,1001,b)); // reverse request order works
    assert(lease.Take("A",101,1002,a));
    assert(a.direction_key==b.direction_key);
    // Both share WAN IPv4 only with distinct source ports: valid.
    src.port_b=src.port_a;
    assert(!lease.Begin("A","B",Resolver(src),1000));
    src.port_b=45552;
    // A moving endpoint during issuance must fail at second capture.
    int reads=0;
    auto drifting=[&](const QByteArray& first,const QByteArray& peer)
         ->std::optional<P2PLocalOfferScope> {
        ++reads;
        auto p=src.Scope(first,peer);
        if(p && reads>=3)++p->physical_port_host;
        return p;
    };
    assert(!lease.Begin("A","B",drifting,1000));
    lease.Clear();
    return 0;
}
