/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_query_v583.h"
#include <cassert>
#include <initializer_list>
struct Lock { unsigned depth,calls,seen; BbQueryMapV583 map; };
static bool lock(void *p,int32_t wait) {
    if (wait!=-1) return false;
    ++static_cast<Lock *>(p)->depth;
    return true;
}
static bool unlock(void *p) { return static_cast<Lock *>(p)->depth-- != 0; }
static BbForeignV583 query(void *p,uintptr_t address) {
    auto *l=static_cast<Lock *>(p);
    ++l->calls;
    l->seen=l->depth;
    return bb_query_v583(&l->map,address);
}
int main() {
    using S=BbArenaStatusV582;
    BbHeapV581 heap{};
    const BbQueryRegionV583 rows[]={{0x1000,0x2000},{0x3000,0x4000}};
    Lock l{0,0,0,{rows,2,true}};
    BbArenaV581 a{&heap,&l,lock,unlock};
    for (unsigned slot : {0x70u,0xa0u}) {
        auto run=[&](uintptr_t p) {return bb_arena_route_v582(a,slot,reinterpret_cast<void *>(p),0,0,query,&l).status;};
        const unsigned calls=l.calls;
        assert(run(0)==S::complete && l.calls==calls);
        assert(run(0x1fff)==S::unsupported && run(0x2000)==S::complete);
        assert(run(0x3000)==S::unsupported && run(0x4000)==S::complete);
        assert(!l.depth && l.seen==(slot==0x70?1u:2u) && l.calls==calls+4);
        l.map.complete=false;
        assert(run(0x2000)==S::unsupported && !l.depth);
        l.map.complete=true;
    }
    const BbQueryRegionV583 overlap[]={{1,3},{2,4}};
    l.map={overlap,2,true};
    assert(bb_query_v583(&l.map,5)==BbForeignV583::unavailable);
    assert(!heap.allocation_count && !heap.available);
}
