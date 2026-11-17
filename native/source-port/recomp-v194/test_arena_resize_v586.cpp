/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_resize_v586.h"
#include "arena_seed_v577.h"
#include <cassert>
#include <cstdlib>
#include <initializer_list>
#include <memory>
#include <new>
struct Trace { unsigned depth,peak; };
static bool lock(void *p,int32_t wait) {
    auto &t=*static_cast<Trace *>(p);
    if (wait!=-1) return false;
    if (++t.depth>t.peak) t.peak=t.depth;
    return true;
}
static bool unlock(void *p) {
    auto &t=*static_cast<Trace *>(p);
    if (!t.depth) return false;
    --t.depth;
    return true;
}
int main() {
    using S=BbArenaStatusV582;
    constexpr size_t n=BB_ARENA_SIZE_V577,align=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> owner(std::calloc(1,n+align),&std::free);
    void *mem=owner.get(); size_t space=n+align;
    assert(mem && std::align(align,n,mem,space));
    alignas(BbHeapV581) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *heap=new (obj+0x28) BbHeapV581{};
    assert(bb_arena_seed_v577(obj,sizeof obj,static_cast<unsigned char *>(mem),n,0));
    for (unsigned slot : {0x60u,0x68u,0x90u,0x98u}) {
        Trace trace{};
        const BbArenaV581 a{heap,&trace,lock,unlock};
        auto resize=[&](void *p,uint64_t size,uint64_t al) {return bb_arena_resize_v586(a,slot,p,size,al);};
        const auto old=resize(nullptr,64,16);
        assert(old.status==S::complete && old.payload && heap->allocation_count==1);
        std::memset(old.payload,0x5a,64);
        const auto fail=resize(old.payload,UINT64_MAX,16);
        assert(fail.status==S::complete && !fail.payload && heap->allocation_count==1);
        const auto next=resize(old.payload,128,4096);
        assert(next.status==S::complete && next.payload && next.payload!=old.payload);
        if (slot==0x68 || slot==0x98) assert(!(reinterpret_cast<uintptr_t>(next.payload)&4095));
        for (unsigned i=0;i<64;++i) assert(static_cast<unsigned char *>(next.payload)[i]==0x5a);
        const auto drop=resize(next.payload,0,3);
        assert(drop.status==S::complete && !drop.payload && !heap->allocation_count);
        assert(!trace.depth && trace.peak==(slot>=0x90?3u:2u) && heap->available==heap->capacity);
    }
}
