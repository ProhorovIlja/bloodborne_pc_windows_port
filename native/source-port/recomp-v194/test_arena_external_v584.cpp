/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_external_v584.h"
#include <cassert>
struct Trace { unsigned depth, seq; bool fail; };
static bool lock(void *p,int32_t t) { if(t!=-1)return false; ++static_cast<Trace *>(p)->depth; return true; }
static bool unlock(void *p) { auto &v=*static_cast<Trace *>(p); if(!v.depth)return false; --v.depth; return true; }
static bool unmap(void *p,uintptr_t a,uint64_t n) {
    auto &v=*static_cast<Trace *>(p); assert(v.depth==2 && a==0x1000 && n==0x1000);
    v.seq=v.seq*10+1; return true;
}
static bool direct(void *p,uint64_t a,uint64_t n) {
    auto &v=*static_cast<Trace *>(p); assert(v.depth==2 && a==0x8000 && n==0x1000);
    v.seq=v.seq*10+2; return !v.fail;
}
static bool flexible(void *p,uintptr_t a,uint64_t n) {
    auto &v=*static_cast<Trace *>(p); assert(v.depth==1 && a==0x4000 && n==0x1000);
    v.seq=v.seq*10+3; return true;
}
int main() {
    using K=BbMemoryKindV584; using S=BbArenaStatusV582;
    const BbQueryRegionV583 rows[]={{0x1000,0x2000},{0x4000,0x5000}};
    BbExternalRecordV584 records[]={{0x1000,0x8000,0x1000,K::direct,false},{0x4000,0,0x1000,K::flexible,false}};
    Trace trace{0,0,true}; BbHeapV581 heap{};
    BbExternalV584 e{{rows,2,true},records,2,&trace,unmap,direct,flexible};
    BbArenaV581 a{&heap,&trace,lock,unlock};
    auto run=[&](unsigned slot,uintptr_t p) { return bb_arena_route_v582(a,slot,reinterpret_cast<void *>(p),0,0,
        bb_external_query_v584,&e,bb_external_free_v584).status; };
    assert(run(0xa0,0x1001)==S::complete && !trace.seq);
    assert(run(0xa0,0x1000)==S::unsupported && records[0].unmapped && trace.seq==12 && !trace.depth);
    trace.fail=false; e.mappings={rows+1,1,true};
    assert(run(0xa0,0x1000)==S::complete && !records[0].base && trace.seq==122 && !trace.depth);
    assert(run(0xa0,0x1000)==S::complete && trace.seq==122);
    assert(run(0x70,0x4000)==S::complete && !records[1].base && trace.seq==1223 && !trace.depth);
    assert(!heap.allocation_count && !heap.available);
}
