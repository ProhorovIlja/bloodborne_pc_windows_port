/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_seed_v577.h"
#include "paleblood_v579/regular_heap.h"
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <new>
using engine::regular_heap::Heap;
extern "C" void *bb_engine_regular_heap_allocate_02485730(Heap *,uint64_t);
extern "C" void *bb_engine_regular_heap_allocate_aligned_02485a60(Heap *,uint64_t,uint64_t);
extern "C" void bb_engine_regular_heap_free_024858a0(Heap *,void *);
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"V580:%d\n",__LINE__); return 1; } } while (0)
int main() {
    constexpr size_t n=BB_ARENA_SIZE_V577,a=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> owner(std::calloc(1,n+a),&std::free);
    void *p=owner.get();
    size_t space=n+a;
    CHECK(p && std::align(a,n,p,space));
    auto *mem=static_cast<unsigned char *>(p);
    alignas(Heap) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *h=new (obj+0x28) Heap{};
    CHECK(bb_arena_seed_v577(obj,sizeof obj,mem,n,0));
    auto alloc=[&](uint64_t k,uint64_t align) { return bb_engine_regular_heap_allocate_aligned_02485a60(h,k,align); };
    auto release=[&](void *k) { bb_engine_regular_heap_free_024858a0(h,k); };
    release(nullptr);
    CHECK(!alloc(8,3) && !alloc(UINT64_MAX,16) && !h->allocation_count);
    void *x=alloc(25,32);
    void *y=alloc(64,4096);
    void *z=bb_engine_regular_heap_allocate_02485730(h,128);
    CHECK(x && y && z && x!=y && x!=z && y!=z);
    CHECK(!(reinterpret_cast<uintptr_t>(x)&31) && !(reinterpret_cast<uintptr_t>(y)&4095));
    CHECK(h->allocation_count==3 && h->available<h->capacity);
    release(y); release(x); release(z);
    CHECK(!h->allocation_count && h->available==n-32 && h->nonempty_lists==(UINT64_C(1)<<26));
    CHECK((h->first_block->next_and_flags&~uintptr_t{3})==reinterpret_cast<uintptr_t>(h->end_block));
    void *whole=alloc(n-40,0);
    CHECK(whole==mem+16 && !h->available && !alloc(1,16));
    release(whole);
    CHECK(h->available==h->capacity && !h->allocation_count);
    return 0;
}
