/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_inspect_v585.h"
#include "arena_seed_v577.h"
#include <cassert>
#include <cstdlib>
#include <memory>
#include <new>
struct Lock { unsigned calls; bool allow; };
static bool lock(void *p,int32_t wait) { auto &l=*static_cast<Lock *>(p); ++l.calls; return wait==-1 && l.allow; }
static bool unlock(void *p) { ++static_cast<Lock *>(p)->calls; return true; }
int main() {
    constexpr size_t n=BB_ARENA_SIZE_V577,a=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> owner(std::calloc(1,n+a),&std::free);
    void *mem=owner.get(); size_t space=n+a;
    assert(mem && std::align(a,n,mem,space));
    alignas(BbHeapV581) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *h=new (obj+0x28) BbHeapV581{};
    Lock l{0,true};
    const BbArenaV581 state{h,&l,lock,unlock};
    auto inspect=[&](unsigned slot,const void *p=nullptr) {return bb_arena_inspect_v585(state,slot,p,obj+0x468);};
    assert(!inspect(0xa8).value && l.calls==2);
    assert(bb_arena_seed_v577(obj,sizeof obj,static_cast<unsigned char *>(mem),n,0));
    assert(inspect(0xa8).value==1 && l.calls==4);
    assert(inspect(0x10).value==0x401 && inspect(0x28).value==n-32 && inspect(0x30).value==n-32);
    assert(inspect(0x38).value==n-40 && !inspect(0x40).value);
    auto *p=bb_engine_regular_heap_allocate_02485730(h,25);
    assert(p && inspect(0x48,p).value==40 && inspect(0x40).value==1);
    assert(inspect(0x38).value==n-88 && inspect(0x30).value==n-80);
    assert(inspect(0x48,obj).status==BbAllocStatusV581::invalid && l.calls==4);
    l.allow=false;
    assert(inspect(0xa8).status==BbAllocStatusV581::lock_failed && l.calls==5);
}
