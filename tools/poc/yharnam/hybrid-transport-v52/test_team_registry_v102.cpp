// SPDX-License-Identifier: GPL-2.0-or-later
// V102 source-compiled native Qt server concurrent co-op pair mesh.
#include "sh_p2p_team_registry_v102.hpp"
#include <QByteArray>
#include <QHash>
#include <QVector>
#include <cassert>
#include <array>
#include <cstdint>
#include <optional>

using namespace SeamlessHunt::Hybrid;
struct World {
    QHash<QByteArray,quint64> epochs;
    QHash<QByteArray,quint16> ports;
    QHash<QByteArray,quint32> virtuals;
    quint64 revision=900;
    bool consent=true;
    void Add(const QByteArray& account,quint64 epoch,quint16 port) {
        epochs.insert(account,epoch);
        ports.insert(account,port);
        virtuals.insert(account,0x0a000001U+port);
    }
    std::optional<P2PLocalOfferScope> Scope(
        const QByteArray& a,const QByteArray& b) const {
        if(!consent || a==b || !epochs.contains(a) || !epochs.contains(b))
            return std::nullopt;
        return P2PLocalOfferScope{
            a,b,epochs.value(a),epochs.value(b),revision,
            0x7f000001U,ports.value(b),virtuals.value(b),31314
        };
    }
    P2PTeamPairRegistryV102::Resolver Resolve() {
        return [this](const QByteArray& a,const QByteArray& b) {
            return Scope(a,b);
        };
    }
};
struct Paired {
    SecurePeerOfferV84 a{},b{};
    PairReadyProofV91::Tag proof_a{},proof_b{};
};
static Paired Receive(P2PTeamPairRegistryV102& registry,
                      const QByteArray& a,const QByteArray& b,
                      std::uint64_t id,quint64 epoch_a,quint64 epoch_b,
                      std::uint64_t now=1001) {
    Paired pair{};
    assert(registry.Take(a,id,epoch_a,now,pair.a));
    assert(registry.Take(b,id,epoch_b,now,pair.b));
    assert(pair.a.pair_binding==id && pair.b.pair_binding==id);
    assert(pair.a.direction_key==pair.b.direction_key);
    assert(PairReadyProofV91::Create(pair.a,now,pair.proof_a));
    assert(PairReadyProofV91::Create(pair.b,now,pair.proof_b));
    return pair;
}
static void ThreePlayerMeshIsolation() {
    World world;world.Add("A",101,45551);world.Add("B",202,45552);
    world.Add("C",303,45553);world.Add("D",404,45554);
    P2PTeamPairRegistryV102 registry;
    std::uint64_t ab=0,ac=0,bc=0,cd=0,bad=17;
    assert(registry.Begin("A","B",world.Resolve(),1000,ab));
    assert(registry.Begin("A","C",world.Resolve(),1000,ac));
    assert(registry.Begin("B","C",world.Resolve(),1000,bc));
    assert(registry.Begin("C","D",world.Resolve(),1000,cd));
    assert(registry.Count()==4 && ab && ac && bc && cd);
    assert(ab!=ac && ac!=bc && bc!=cd && ab!=bc && ab!=cd);
    assert(registry.AvailableFor("A",1001).size()==2);
    assert(registry.AvailableFor("B",1001).size()==2);
    assert(registry.AvailableFor("C",1001).size()==3);
    assert(registry.AvailableFor("D",1001).size()==1);
    assert(registry.AvailableFor("stranger",1001).empty());
    assert(!registry.Begin("B","A",world.Resolve(),1001,bad));
    assert(bad==0);
    assert(!registry.Begin("C","C",world.Resolve(),1001,bad));
    assert(bad==0);
    // An authenticated member of A-C cannot use that identity to
    // obtain A-B's ticket for C or clear A-B with a bogus pair selector.
    SecurePeerOfferV84 forged{};
    bool both=false;
    assert(!registry.Take("C",ab,303,1001,forged));
    assert(!registry.MarkReady("C",ab,303,{},1001,both));
    assert(!registry.Take("A",0xdeadbeefULL,101,1001,forged));
    assert(registry.Count()==4);
    auto pair_ab=Receive(registry,"A","B",ab,101,202);
    auto pair_ac=Receive(registry,"A","C",ac,101,303);
    auto pair_bc=Receive(registry,"B","C",bc,202,303);
    auto pair_cd=Receive(registry,"C","D",cd,303,404);
    assert(pair_ab.a.direction_key!=pair_ac.a.direction_key);
    assert(pair_ab.a.direction_key!=pair_bc.a.direction_key);
    assert(pair_ac.a.direction_key!=pair_bc.a.direction_key);
    assert(registry.MarkReady("A",ab,101,pair_ab.proof_a,1002,both) && !both);
    assert(registry.MarkReady("B",ab,202,pair_ab.proof_b,1003,both) && both);
    assert(registry.BothReady("A",ab,1004));
    assert(registry.MarkReady("A",ac,101,pair_ac.proof_a,1002,both) && !both);
    assert(registry.MarkReady("C",ac,303,pair_ac.proof_b,1003,both) && both);
    assert(registry.MarkReady("B",bc,202,pair_bc.proof_a,1004,both) && !both);
    assert(registry.MarkReady("C",bc,303,pair_bc.proof_b,1005,both) && both);
    assert(registry.MarkReady("C",cd,303,pair_cd.proof_a,1004,both) && !both);
    assert(registry.MarkReady("D",cd,404,pair_cd.proof_b,1005,both) && both);
    assert(registry.BothReady("D",cd,1006));
    assert(!registry.MarkReady("A",ab,101,pair_ab.proof_a,1006,both));
    assert(registry.Count()==3); // revoke only A-B
    assert(registry.BothReady("A",ac,1006));
    assert(registry.BothReady("C",bc,1006));
    assert(registry.RevokeAccount("A")==1); // only A-C remains for A
    assert(registry.Count()==2);
    assert(registry.BothReady("C",bc,1006));
    assert(registry.BothReady("D",cd,1006));
    assert(!registry.BothReady("A",ac,1006));
    assert(registry.RevokeAccount("C")==2); // B-C and C-D
    assert(registry.Count()==0);
    assert(!registry.RevokePair(ab));
}
// A team is host + FOUR guests: 5*4/2=10 independent P2P pair routes.
// A newcomer outside this team must NEVER inherit a former team's grant.
static void FiveHunterFullMesh() {
    World world;
    const QVector<QByteArray> hunters={"host","guest1","guest2","guest3","guest4"};
    for(qsizetype i=0;i<hunters.size();++i)
        world.Add(hunters[i],static_cast<quint64>(101+i),
                  static_cast<quint16>(43000+i));
    P2PTeamPairRegistryV102 registry;
    QSet<std::uint64_t> grants;
    for(qsizetype i=0;i<hunters.size();++i)
        for(qsizetype j=i+1;j<hunters.size();++j) {
            std::uint64_t pair=0;
            assert(registry.Begin(hunters[i],hunters[j],world.Resolve(),1000,pair));
            assert(pair && !grants.contains(pair));
            grants.insert(pair);
        }
    assert(grants.size()==10);
    assert(registry.Count()==10);
    for(const auto& member:hunters)
        assert(registry.AvailableFor(member,1001).size()==4);
    // Peer cannot claim a sixth team membership simply by asking TLS to
    // look up or take a grant; team membership lives in YT BloodborneWorld.
    assert(registry.AvailableFor("sixth",1001).empty());
    SecurePeerOfferV84 forged{};
    for(const auto grant:grants)
        assert(!registry.Take("sixth",grant,888,1002,forged));
    assert(registry.Count()==10);
    std::vector<std::pair<QByteArray,QByteArray>> survivors;
    for(qsizetype i=0;i<4;++i)
        for(qsizetype j=i+1;j<4;++j)
            survivors.emplace_back(hunters[i],hunters[j]);
    // Server now sees only FOUR surviving game accounts.
    assert(registry.RevokeNotIn(survivors)==4);
    assert(registry.RevokeNotIn(survivors)==0); // idempotent
    assert(registry.Count()==6);
    for(const auto& member:QVector<QByteArray>{"host","guest1","guest2","guest3"})
        assert(registry.AvailableFor(member,1003).size()==3);
    assert(registry.AvailableFor("guest4",1003).empty());
    registry.Sweep(11000);
    assert(registry.Count()==0);
}
static void EpochConsentAndLimits() {
    World world;
    world.Add("A",1,40001);world.Add("B",2,40002);
    world.Add("C",3,40003);
    P2PTeamPairRegistryV102 registry;
    std::uint64_t id=0;
    assert(registry.Begin("A","B",world.Resolve(),1000,id));
    auto previous=id;
    world.epochs.insert("B",22);
    SecurePeerOfferV84 ticket{};
    assert(!registry.Take("A",id,1,1001,ticket));
    assert(registry.Count()==0);
    assert(registry.Begin("A","B",world.Resolve(),1002,id));
    assert(id!=previous);
    assert(registry.Take("B",id,22,1003,ticket));
    world.consent=false;
    assert(!registry.Take("A",id,1,1004,ticket));
    assert(registry.Count()==0);
    world.consent=true;
    assert(registry.Begin("A","B",world.Resolve(),1005,id));
    assert(registry.AvailableFor("A",11005).empty());
    registry.Sweep(11005);
    assert(registry.Count()==0);

    // Fixed per-member limit prevents one hunter receiving 512 simultaneous
    // pair keys; other disjoint pairs can still occupy the remaining table.
    for(int i=0;i<16;++i) {
        const auto peer=QByteArray("X")+QByteArray::number(i);
        world.Add(peer,100+static_cast<quint64>(i),
                  static_cast<quint16>(41000+i));
        assert(registry.Begin("A",peer,world.Resolve(),12000,id));
    }
    world.Add("X16",116,41116);
    assert(!registry.Begin("A","X16",world.Resolve(),12000,id));
    assert(id==0 && registry.Count()==16);
    assert(registry.RevokeAccount("A")==16);
    assert(registry.Count()==0);

    // Global cap of 512 disjoint pairs, plus 513th refused, then reused
    // after an old generation expires. No uncontrolled memory growth.
    for(int i=0;i<512;++i) {
        const auto a=QByteArray("P")+QByteArray::number(i);
        const auto b=QByteArray("Q")+QByteArray::number(i);
        world.Add(a,5000+static_cast<quint64>(i),
                  static_cast<quint16>(20000+i*2));
        world.Add(b,6000+static_cast<quint64>(i),
                  static_cast<quint16>(20001+i*2));
        assert(registry.Begin(a,b,world.Resolve(),20000,id));
    }
    assert(registry.Count()==512);
    world.Add("overflowA",9001,43001);
    world.Add("overflowB",9002,43002);
    assert(!registry.Begin("overflowA","overflowB",world.Resolve(),20001,id));
    assert(id==0);
    registry.Sweep(30000);
    assert(registry.Count()==0);
    assert(registry.Begin("overflowA","overflowB",world.Resolve(),30001,id));
    assert(registry.Count()==1);
    registry.ClearAll();
    assert(registry.Count()==0);
}
int main() {
    ThreePlayerMeshIsolation();
    FiveHunterFullMesh();
    EpochConsentAndLimits();
    return 0;
}
