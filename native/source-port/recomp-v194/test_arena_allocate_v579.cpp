/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_seed_v577.h"
#include "paleblood_v579/regular_heap.h"
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <new>

extern "C" void *bb_engine_regular_heap_allocate_02485730(engine::regular_heap::Heap *,uint64_t);
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"V579:%d\n",__LINE__); return 1; } } while (0)
int main() {
    using engine::regular_heap::Heap;
    constexpr size_t n=BB_ARENA_SIZE_V577, a=BB_ARENA_ALIGN_V577;
    constexpr uint64_t capacity=n-32;
    std::unique_ptr<void,decltype(&std::free)> owner(std::calloc(1,n+a),&std::free);
    void *p=owner.get();
    size_t space=n+a;
    CHECK(p && std::align(a,n,p,space));
    auto *mem=static_cast<unsigned char *>(p);
    alignas(Heap) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *heap=new (obj+0x28) Heap{};
    auto allocate=[&](uint64_t request) { return bb_engine_regular_heap_allocate_02485730(heap,request); };
    CHECK(bb_arena_seed_v577(obj,sizeof obj,mem,n,0));
    CHECK(allocate(UINT64_MAX)==nullptr && heap->available==capacity && !heap->allocation_count);
    CHECK(allocate(0)==mem+16 && heap->available==capacity-32);
    CHECK(allocate(25)==mem+48 && heap->available==capacity-80 && heap->allocation_count==2);
    CHECK(bb_arena_seed_v577(obj,sizeof obj,mem,n,0));
    CHECK(allocate(capacity-24)==mem+16 && heap->available==16 && !heap->nonempty_lists);
    CHECK(!allocate(0) && heap->available==16 && heap->allocation_count==1);
    CHECK(bb_arena_seed_v577(obj,sizeof obj,mem,n,0));
    CHECK(allocate(capacity-8)==mem+16 && !heap->available && !heap->nonempty_lists);
    CHECK(!allocate(0) && heap->allocation_count==1);
    return 0;
}
