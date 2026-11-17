/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_slots_v581.h"
#include "arena_seed_v577.h"
#include "native_startup_mutex_v413.h"
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <new>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"V581:%d\n",__LINE__); return 1; } } while (0)
struct Lock { ShytStartupMutexV413 m; unsigned acquired,released; bool reject; };
static bool lock(void *p,int32_t wait) {
    auto &l=*static_cast<Lock *>(p);
    if (wait!=-1 || l.reject || !shyt_startup_mutex_lock_v413(&l.m)) return false;
    ++l.acquired;
    return true;
}
static bool unlock(void *p) {
    auto &l=*static_cast<Lock *>(p);
    ++l.released;
    return shyt_startup_mutex_unlock_v413(&l.m);
}
int main() {
    constexpr size_t n=BB_ARENA_SIZE_V577, align=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> raw(std::calloc(1,n+align),&std::free);
    void *mem=raw.get(); size_t space=n+align;
    CHECK(mem && std::align(align,n,mem,space));
    alignas(BbHeapV581) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *h=new (obj+0x28) BbHeapV581{};
    CHECK(bb_arena_seed_v577(obj,sizeof obj,static_cast<unsigned char *>(mem),n,0));
    Lock l{};
    CHECK(shyt_startup_mutex_init_v413(&l.m,2));
    const BbArenaV581 a{h,&l,lock,unlock};
    const auto *v=bb_arena_slots_v581();
    l.reject=true;
    CHECK(v->allocate(a,64).status==BbAllocStatusV581::lock_failed && !h->allocation_count);
    l.reject=false;
    auto x=v->allocate(a,25), y=v->aligned(a,64,4096), z=v->aligned(a,64,3);
    CHECK(x.status==BbAllocStatusV581::complete && x.payload &&
          y.status==BbAllocStatusV581::complete && y.payload &&
          !(reinterpret_cast<uintptr_t>(y.payload)&4095));
    CHECK(z.status==BbAllocStatusV581::complete && !z.payload &&
          h->allocation_count==2 && l.acquired==3 && l.released==3);
    CHECK(shyt_startup_mutex_lock_v413(&l.m));
    bb_engine_regular_heap_free_024858a0(h,x.payload);
    bb_engine_regular_heap_free_024858a0(h,y.payload);
    CHECK(shyt_startup_mutex_unlock_v413(&l.m));
    CHECK(h->available==h->capacity && !h->allocation_count);
    CHECK(shyt_startup_mutex_destroy_v413(&l.m));
    return 0;
}
