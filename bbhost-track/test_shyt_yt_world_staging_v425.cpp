// SPDX-License-Identifier: GPL-2.0-or-later
// Original YT protobuf tags, independently cross-checked in V421/V422
// against upstream v1.4.0 generated bbcoop::Envelope in CI.
#include "shyt_yt_world_staging_v425.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
using Stage=SeamlessHunt::YtWorldStagingV425;
using Bytes=std::vector<std::uint8_t>;
static void V(Bytes& b,std::uint64_t n) {
    while(n>=128u){b.push_back(static_cast<std::uint8_t>(n|128u));n>>=7u;}
    b.push_back(static_cast<std::uint8_t>(n));
}
static void N(Bytes& b,unsigned field,std::uint64_t value) {
    V(b,static_cast<std::uint64_t>(field)*8u);V(b,value);
}
static void B(Bytes& b,unsigned field,const Bytes& inner) {
    V(b,static_cast<std::uint64_t>(field)*8u+2u);
    V(b,inner.size());
    b.insert(b.end(),inner.begin(),inner.end());
}
static Bytes Snap(std::uint64_t epoch,std::uint64_t last) {
    Bytes body,env,map,handles,entry;
    N(body,1u,epoch);N(body,2u,last);
    N(map,1u,0x18000000u);V(handles,55u);V(handles,300u);
    B(map,2u,handles);B(body,3u,map);
    if(last) {
        N(entry,1u,last);
        N(entry,2u,0x18000000u);
        N(entry,3u,5u);
        B(body,11u,entry);
    }
    B(env,7u,body);
    return env;
}
static Bytes Delta(std::uint64_t epoch,std::uint64_t last,
                   std::uint64_t first,std::uint32_t count) {
    Bytes body,env;
    N(body,1u,epoch);N(body,2u,last);
    for(std::uint32_t i=0;i<count;++i) {
        Bytes entry;
        N(entry,1u,first+i);
        N(entry,2u,0x18000000u);
        N(entry,3u,1u);N(entry,4u,55u);
        B(body,3u,entry);
    }
    B(env,5u,body);
    return env;
}
int main() {
    Stage stage;
    const auto snapshot=Snap(77u,9u);
    assert(!stage.StageSnapshot(snapshot,0u,9u));
    assert(!stage.Active() && stage.Stats().rejected==1u);
    assert(stage.StageSnapshot(snapshot,77u,9u));
    assert(stage.Active() && stage.Epoch()==77u &&
           stage.StagedCursor()==9u && stage.PendingPackets()==1u &&
           stage.StagedBytes()==snapshot.size());
    const auto* snap=stage.Peek(0u);
    assert(snap && snap->kind==Stage::Kind::Snapshot &&
           snap->wire==snapshot && !stage.Peek(1u));
    assert(!stage.StageSnapshot(snapshot,77u,9u));
    assert(!stage.StageEntries(Delta(88u,11u,10u,2u),88u,11u,10u,11u,2u));
    assert(!stage.StageEntries(Delta(77u,12u,12u,1u),77u,12u,12u,12u,1u));
    assert(stage.PendingPackets()==1u && stage.StagedCursor()==9u);
    const auto first=Delta(77u,11u,10u,2u);
    assert(stage.StageEntries(first,77u,11u,10u,11u,2u));
    assert(stage.StagedCursor()==11u && stage.PendingPackets()==2u);
    const auto* batch=stage.Peek(1u);
    assert(batch && batch->wire==first && batch->first==10u &&
           batch->tail==11u && batch->skip_through==9u);
    // Rerouting/restored server may send a partially overlapping window.
    // Keep exact original bytes but identify already staged sequence <=11.
    const auto overlap=Delta(77u,12u,11u,2u);
    assert(stage.StageEntries(overlap,77u,12u,11u,12u,2u));
    batch=stage.Peek(2u);
    assert(batch && batch->skip_through==11u && batch->first==11u &&
           batch->tail==12u && batch->wire==overlap);
    assert(!stage.StageEntries(overlap,77u,12u,11u,12u,2u));
    assert(!stage.StageEntries(Delta(77u,13u,13u,1u),77u,13u,13u,13u,2u));
    assert(stage.StagedCursor()==12u && stage.PendingPackets()==3u);
    stage.Revoke();
    assert(!stage.Active() && stage.StagedCursor()==0u &&
           stage.StagedBytes()==0u && stage.PendingPackets()==0u &&
           !stage.Peek(0u));
    assert(!stage.StageSnapshot(snapshot,77u,9u)); // cannot rearm same link
    assert(stage.Stats().revoked==1u);

    Stage limit;
    const auto fresh=Snap(4u,0u);
    assert(limit.StageSnapshot(fresh,4u,0u));
    for(std::uint32_t i=1u;i<=Stage::MaxDeltaBatches;++i)
        assert(limit.StageEntries(Delta(4u,i,i,1u),4u,i,i,i,1u));
    assert(limit.PendingPackets()==Stage::MaxDeltaBatches+1u);
    const auto next=Stage::MaxDeltaBatches+1u;
    assert(!limit.StageEntries(Delta(4u,next,next,1u),
                               4u,next,next,next,1u));
    assert(limit.StagedCursor()==Stage::MaxDeltaBatches);
    // Error is surfaced to the controller, which must fail closed:
    // NEVER silently evict a real world delta for space.
    limit.Revoke();
    assert(!limit.Active() && limit.Stats().revoked==1u);

    Stage bytes_cap;
    assert(bytes_cap.StageSnapshot(fresh,4u,0u));
    // A valid-sized but excessively numerous set of messages cannot
    // grow the held memory without bound.
    for(std::uint32_t i=1u;i<=Stage::MaxDeltaBatches;++i) {
        const auto entry=Delta(4u,i,i,1u);
        assert(bytes_cap.StageEntries(entry,4u,i,i,i,1u));
    }
    assert(bytes_cap.StagedBytes()<=Stage::MaxStagedBytes);
    std::puts("SHYT_V425_YT_IMMUTABLE_WORLD_STAGING_PASS");
}
