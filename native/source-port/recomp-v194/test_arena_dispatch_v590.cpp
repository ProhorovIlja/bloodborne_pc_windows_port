/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_dispatch_v590.h"
#include "native_startup_mutex_v413.h"
#include <cassert>
#include <cstdlib>
#include <initializer_list>
#include <memory>
#include <new>
struct Lock { ShytStartupMutexV413 mutex; unsigned depth; };
static bool acquire(void *p,int32_t timeout) {
    auto &l=*static_cast<Lock *>(p);
    if (timeout!=-1 || !shyt_startup_mutex_lock_v413(&l.mutex)) return false;
    ++l.depth; return true;
}
static bool release(void *p) {
    auto &l=*static_cast<Lock *>(p);
    if (!l.depth || !shyt_startup_mutex_unlock_v413(&l.mutex)) return false;
    --l.depth; return true;
}
int main() {
    using S=BbArenaStatusV582;
    constexpr size_t n=BB_ARENA_SIZE_V577, a=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> raw(std::calloc(1,n+a),&std::free);
    void *p=raw.get(); size_t room=n+a;
    assert(p && std::align(a,n,p,room));
    alignas(BbHeapV581) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *heap=new (obj+0x28) BbHeapV581{};
    assert(bb_arena_seed_v577(obj,sizeof obj,static_cast<unsigned char *>(p),n,0));
    Lock l{}; assert(shyt_startup_mutex_init_v413(&l.mutex,2));
    const BbMutexControlV588 ctl{&l,[](void *){return true;},
        [](void *z){return acquire(z,-1)?0u:0x80020016u;},
        [](void *z){return release(z)?0u:0x80020016u;},[](void *,unsigned){std::abort();}};
    const BbArenaDispatchV590 x{{heap,&l,acquire,release},obj,nullptr,&ctl};
    auto call=[&](unsigned s,void *q=nullptr,uint64_t len=0,uint64_t al=0) {
        return bb_arena_dispatch_v590(x,s,q,len,al);
    };
    assert(call(0x08,obj).status==S::unsupported && call(0xd8).status==S::unsupported);
    for (unsigned s:{0u,0x18u,0x78u,0xb8u}) assert(call(s).status==S::complete);
    unsigned char kind[5]={0,0,0,0,99};
    assert(call(0x20,kind,4).value==reinterpret_cast<uintptr_t>(kind) && kind[0]==0x3b && kind[4]==99);
    assert(call(0x10).value==0x401 && call(0x28).value==n-32 && call(0x38).value==n-40);
    assert(call(0xa8).value==1 && call(0xc0).status==S::complete && l.depth==1);
    for (unsigned s:{0x50u,0x58u,0x80u,0x88u}) {
        const auto q=call(s,nullptr,64,32);
        assert(q.status==S::complete && q.value);
        auto *v=reinterpret_cast<void *>(q.value);
        assert(call(0x48,v).value>=64 && call(0xb0,v).value==1 && call(0xd0,v).value==0);
        assert(call(s<0x80?0x70:0xa0,v).status==S::complete);
    }
    for (unsigned s:{0x60u,0x68u,0x90u,0x98u}) {
        const auto q=call(s,nullptr,64,32);
        assert(q.status==S::complete && q.value);
        assert(call(s,reinterpret_cast<void *>(q.value),0,32).status==S::complete);
    }
    assert(call(0x40).value==0 && call(0x30).value==n-32 && l.depth==1);
    assert(call(0xc8).status==S::complete && !l.depth && shyt_startup_mutex_destroy_v413(&l.mutex));
}
