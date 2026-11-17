/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_routes_v582.h"
#include "arena_seed_v577.h"
#include "native_startup_mutex_v413.h"
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <new>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"V582:%d\n",__LINE__); return 1; } } while (0)
struct Lock { ShytStartupMutexV413 m; unsigned calls,depth,peak,deny; };
static bool acquire(void *p,int32_t timeout) {
    auto &l=*static_cast<Lock *>(p);
    if (timeout!=-1 || ++l.calls==l.deny || !shyt_startup_mutex_lock_v413(&l.m)) return false;
    if (++l.depth>l.peak) l.peak=l.depth;
    return true;
}
static bool release(void *p) {
    auto &l=*static_cast<Lock *>(p);
    if (!l.depth || !shyt_startup_mutex_unlock_v413(&l.m)) return false;
    --l.depth;
    return true;
}
int main() {
    using S=BbArenaStatusV582;
    constexpr size_t n=BB_ARENA_SIZE_V577,align=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> owner(std::calloc(1,n+align),&std::free);
    void *mem=owner.get(); size_t space=n+align;
    CHECK(mem && std::align(align,n,mem,space));
    alignas(BbHeapV581) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *heap=new (obj+0x28) BbHeapV581{};
    CHECK(bb_arena_seed_v577(obj,sizeof obj,static_cast<unsigned char *>(mem),n,0));
    Lock l{};
    CHECK(shyt_startup_mutex_init_v413(&l.m,2));
    const BbArenaV581 a{heap,&l,acquire,release};
    auto call=[&](unsigned slot,void *p=nullptr,uint64_t bytes=0,uint64_t alignment=0) {
        return bb_arena_route_v582(a,slot,p,bytes,alignment);
    };
    CHECK(call(0x98).status==S::unsupported && l.calls==0);
    l.deny=2;
    CHECK(call(0x80,nullptr,25).status==S::lock_failed && l.calls==2 && l.depth==0 &&
          heap->available==heap->capacity && !heap->allocation_count);
    CHECK(call(0xa0,obj).status==S::unsupported && !l.depth && !heap->allocation_count);
    CHECK(call(0x70).status==S::complete && !l.depth);
    auto p=call(0x50,nullptr,25), q=call(0x88,nullptr,64,4096);
    CHECK(p.status==S::complete && p.payload && q.status==S::complete && q.payload &&
          !(reinterpret_cast<uintptr_t>(q.payload)&4095) && heap->allocation_count==2);
    CHECK(call(0xa0,p.payload).status==S::complete && call(0x70,q.payload).status==S::complete);
    CHECK(l.peak==2 && !l.depth && heap->available==heap->capacity && !heap->allocation_count);
    CHECK(shyt_startup_mutex_destroy_v413(&l.m));
    return 0;
}
