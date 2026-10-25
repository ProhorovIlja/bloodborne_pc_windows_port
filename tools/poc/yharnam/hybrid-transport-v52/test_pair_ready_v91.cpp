// SPDX-License-Identifier: GPL-2.0-or-later
// V91 source-only same-server two separate TLS possession proofs.
// No public network listener, no authority from a UDP client, no Direct Arm.
#include "sh_pair_ready_v91.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace SeamlessHunt::Hybrid;
static AccountDigestV84 Id(unsigned seed) {
    AccountDigestV84 out{};
    for(unsigned i=0;i<out.size();++i)
        out[i]=static_cast<std::uint8_t>(seed+i);
    return out;
}
static SecurePeerOfferV84 OfferA() {
    SecurePeerOfferV84 x{};
    x.recipient_account=Id(15);x.sender_account=Id(65);
    x.session_epoch=101;x.world_revision=303;x.pair_binding=404;
    x.issued_ms=1000;x.expires_ms=2000;
    x.peer_ipv4_nbo=0x01020304;x.peer_port_nbo=44011;
    x.peer_virtual_ipv4_nbo=0x0a010203;x.peer_virtual_port_nbo=31314;
    x.direction_key=Id(110);
    return x;
}
static SecurePeerOfferV84 OfferB(const SecurePeerOfferV84& a){
    auto b=a;
    b.recipient_account=a.sender_account;b.sender_account=a.recipient_account;
    b.session_epoch=202;
    b.peer_port_nbo=44012;
    return b;
}
int main(){
    const auto a=OfferA(),b=OfferB(a);
    PairReadyProofV91::Tag proof_a{},proof_b{},other{};
    assert(PairReadyProofV91::Create(a,1001,proof_a));
    assert(PairReadyProofV91::Create(b,1001,proof_b));
    assert(proof_a!=proof_b);
    assert(proof_a!=a.direction_key && proof_b!=b.direction_key);
    assert(PairKeyScheduleV89::Derive(a,true,
            PairKeyPurposeV89::NatProbe,1001,other));
    assert(other!=proof_a);
    assert(PairKeyScheduleV89::Derive(a,true,
            PairKeyPurposeV89::GameData,1001,other));
    assert(other!=proof_a);
    PairReadyGateV91 gate;
    using Result=PairReadyGateV91::Result;
    assert(gate.Prepare(a,b,1001));
    assert(gate.PairBinding()==404);
    assert(!gate.BothReady(1001));
    assert(gate.Mark(a.recipient_account,101,303,true,proof_a,1002)==
           Result::WaitingPeer);
    assert(!gate.BothReady(1002));
    assert(gate.Mark(b.recipient_account,202,303,true,proof_b,1003)==
           Result::BothReady);
    assert(gate.BothReady(1003));
    assert(!gate.BothReady(2000));
    assert(gate.Mark(a.recipient_account,101,303,true,proof_a,1004)==
           Result::Denied);
    assert(!gate.BothReady(1004)); // replay completely revokes pair
    assert(gate.PairBinding()==0);

    const auto assert_denied=[&](const AccountDigestV84& who,
                                  std::uint64_t epoch,std::uint64_t world,
                                  bool consent,
                                  const PairReadyProofV91::Tag& proof,
                                  std::uint64_t time) {
        assert(gate.Prepare(a,b,1001));
        assert(gate.Mark(who,epoch,world,consent,proof,time)==Result::Denied);
        assert(gate.PairBinding()==0);
    };
    assert_denied(a.recipient_account,102,303,true,proof_a,1002);
    assert_denied(a.recipient_account,101,304,true,proof_a,1002);
    assert_denied(a.recipient_account,101,303,false,proof_a,1002);
    assert_denied(Id(230),101,303,true,proof_a,1002);
    assert_denied(a.recipient_account,101,303,true,proof_b,1002);
    assert_denied(a.recipient_account,101,303,true,proof_a,2000);
    assert_denied(a.recipient_account,101,303,true,proof_a,999);
    auto wrong=proof_a;wrong[0]^=1;
    assert_denied(a.recipient_account,101,303,true,wrong,1002);
    auto bad=b;bad.pair_binding++;
    assert(!gate.Prepare(a,bad,1001));
    bad=b;bad.world_revision++;
    assert(!gate.Prepare(a,bad,1001));
    bad=b;bad.sender_account=Id(180);
    assert(!gate.Prepare(a,bad,1001));
    bad=b;bad.direction_key[31]^=1;
    assert(!gate.Prepare(a,bad,1001));
    bad=b;bad.expires_ms++;
    assert(!gate.Prepare(a,bad,1001));
    assert(!PairReadyProofV91::Create(a,2000,other));
    assert((other==PairReadyProofV91::Tag{}));
    return 0;
}
