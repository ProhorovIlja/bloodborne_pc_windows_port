// SPDX-License-Identifier: GPL-2.0-or-later
// V101 actual Qt/OpenSSL server pair isolation, bounded capacity and expiry.
#include "sh_p2p_pair_registry_v101.hpp"
#include <QByteArray>
#include <QHash>
#include <QtGlobal>
#include <cassert>
#include <cstdint>
#include <optional>
#include <array>

using namespace SeamlessHunt::Hybrid;
struct LiveWorld {
    QHash<QByteArray,QByteArray> peer;
    QHash<QByteArray,quint16> ports;
    QHash<QByteArray,quint64> epochs;
    QHash<QByteArray,quint32> virtuals;
    quint64 revision=303;
    bool opted=true;
    static QByteArray Name(int id) {
        return QByteArray("hunter-")+QByteArray::number(id);
    }
    void Add(int number) {
        const auto a=Name(number*2),b=Name(number*2+1);
        peer.insert(a,b);peer.insert(b,a);
        ports.insert(a,static_cast<quint16>(10000+number*2));
        ports.insert(b,static_cast<quint16>(10001+number*2));
        epochs.insert(a,static_cast<quint64>(number*2+1));
        epochs.insert(b,static_cast<quint64>(number*2+2));
        virtuals.insert(a,0x0a000001U+static_cast<quint32>(number*2));
        virtuals.insert(b,0x0a000002U+static_cast<quint32>(number*2));
    }
    std::optional<P2PLocalOfferScope> Capture(const QByteArray& to,
                                               const QByteArray& other) const {
        if(!opted || peer.value(to)!=other || to==other ||
           !epochs.contains(to) || !epochs.contains(other))
            return std::nullopt;
        return P2PLocalOfferScope{
            to,other,epochs.value(to),epochs.value(other),revision,
            0x7f000001U,ports.value(other),virtuals.value(other),31314
        };
    }
    P2PPairRegistryV101::Resolver Resolver() {
        return [this](const QByteArray& to,const QByteArray& other) {
            return Capture(to,other);
        };
    }
};
static void IndependentPairsAndReceipt() {
    LiveWorld world;
    world.Add(0);world.Add(1);
    P2PPairRegistryV101 registry;
    const auto a=LiveWorld::Name(0),b=LiveWorld::Name(1);
    const auto c=LiveWorld::Name(2),d=LiveWorld::Name(3);
    SecurePeerOfferV84 offer_a{},offer_b{},offer_c{},offer_d{},stranger{};
    bool both=false;
    assert(registry.Begin(a,b,world.Resolver(),1000));
    assert(registry.Begin(c,d,world.Resolver(),1000));
    assert(registry.Count()==2);
    assert(!registry.Begin(a,c,world.Resolver(),1000)); // ambiguous member
    assert(!registry.Begin(b,a,world.Resolver(),1000)); // order irrelevant
    assert(!registry.Take("attacker",1,1001,stranger));
    assert(registry.Count()==2);
    assert(!registry.MarkReady("attacker",1,{},1001,both));
    assert(registry.Count()==2 && !both);
    assert(registry.Take(a,1,1001,offer_a));
    assert(registry.Take(b,2,1002,offer_b));
    assert(registry.Take(c,3,1002,offer_c));
    assert(registry.Take(d,4,1003,offer_d));
    assert(offer_a.pair_binding==offer_b.pair_binding);
    assert(offer_c.pair_binding==offer_d.pair_binding);
    assert(offer_a.pair_binding!=offer_c.pair_binding);
    assert(offer_a.direction_key==offer_b.direction_key);
    assert(offer_c.direction_key==offer_d.direction_key);
    assert(offer_a.direction_key!=offer_c.direction_key);
    PairReadyProofV91::Tag proof_a{},proof_b{},proof_c{},proof_d{};
    assert(PairReadyProofV91::Create(offer_a,1002,proof_a));
    assert(PairReadyProofV91::Create(offer_b,1002,proof_b));
    assert(PairReadyProofV91::Create(offer_c,1003,proof_c));
    assert(PairReadyProofV91::Create(offer_d,1003,proof_d));
    assert(registry.MarkReady(c,3,proof_c,1004,both) && !both);
    assert(registry.MarkReady(a,1,proof_a,1005,both) && !both);
    assert(registry.MarkReady(b,2,proof_b,1006,both) && both);
    assert(registry.BothReadyFor(a,1006));
    assert(!registry.BothReadyFor(c,1006));
    assert(registry.MarkReady(d,4,proof_d,1007,both) && both);
    assert(registry.BothReadyFor(c,1007));
    assert(registry.Count()==2);
    // A replay only invalidates A-B. C-D stays ready and unmodified.
    assert(!registry.MarkReady(a,1,proof_a,1008,both));
    assert(registry.Count()==1);
    assert(!registry.HasOutstandingFor(b,1008));
    assert(registry.BothReadyFor(d,1008));
    assert(!registry.RevokeRecipient("attacker"));
    assert(registry.Count()==1);
    assert(registry.RevokeRecipient(d));
    assert(registry.Count()==0);
    assert(registry.Begin(a,b,world.Resolver(),1009));
    assert(!registry.Take(a,2,1010,stranger)); // wrong epoch revokes A-B
    assert(registry.Count()==0);
    assert(registry.Begin(a,b,world.Resolver(),1011));
    world.epochs.insert(b,88);
    assert(!registry.Take(a,1,1012,stranger)); // changed world generation
    assert(registry.Count()==0);
    // A NEW grant with matching current epochs must succeed. Old master
    // must not survive a revoked generation change.
    assert(registry.Begin(a,b,world.Resolver(),1013));
    assert(registry.Take(a,1,1014,offer_a));
    assert(registry.Take(b,88,1014,offer_b));
    assert(offer_a.pair_binding==offer_b.pair_binding);
    assert(offer_a.session_epoch==1 && offer_b.session_epoch==88);
    registry.ClearAll();
}
static void CapacityExpiryAndConsent() {
    LiveWorld world;
    P2PPairRegistryV101 registry;
    assert(registry.Count()==0);
    for(int i=0;i<static_cast<int>(P2PPairRegistryV101::kMaxPairs);++i) {
        world.Add(i);
        assert(registry.Begin(LiveWorld::Name(i*2),LiveWorld::Name(i*2+1),
                              world.Resolver(),1000));
    }
    assert(registry.Count()==P2PPairRegistryV101::kMaxPairs);
    world.Add(static_cast<int>(P2PPairRegistryV101::kMaxPairs));
    assert(!registry.Begin(
        LiveWorld::Name(1024),LiveWorld::Name(1025),
        world.Resolver(),1001)); // hard memory cap
    assert(registry.Count()==P2PPairRegistryV101::kMaxPairs);
    // A late issue on A must not erase unrelated B or allow expired master.
    SecurePeerOfferV84 bad{};
    assert(!registry.Take(LiveWorld::Name(0),1,11000,bad));
    assert(registry.Count()==P2PPairRegistryV101::kMaxPairs-1);
    registry.Sweep(11000);
    assert(registry.Count()==0); // all independent master keys zeroized
    assert(registry.Begin(LiveWorld::Name(1024),LiveWorld::Name(1025),
                          world.Resolver(),11001));
    assert(registry.Count()==1);
    world.opted=false;
    assert(!registry.Take(LiveWorld::Name(1024),1025,11002,bad));
    assert(registry.Count()==0);
    world.opted=true;
    assert(registry.Begin(LiveWorld::Name(1024),LiveWorld::Name(1025),
                          world.Resolver(),11003));
    registry.ClearAll();
    assert(registry.Count()==0);
}
int main() {
    IndependentPairsAndReceipt();
    CapacityExpiryAndConsent();
    return 0;
}
