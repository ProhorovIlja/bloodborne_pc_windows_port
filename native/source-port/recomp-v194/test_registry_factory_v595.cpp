/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <pthread.h>

namespace engine::regular_heap { struct Heap; }
extern "C" void *bb_engine_regular_heap_allocate_02485730(engine::regular_heap::Heap *,uint64_t);
struct Area { uintptr_t heap,start,end; };
struct Ops {
    void *ctx;
    int (*lock)(void *),(*unlock)(void *);
    void (*overlap)(void *);
    Area *(*allocate)(void *,size_t);
    void (*release)(void *,Area *);
};
extern "C" void *bb_registry_factory_cold_v595(unsigned char *,size_t,unsigned char *,size_t,
    int (*)(void *),int (*)(void *),void *(*)(void *,size_t,size_t),void *(*)(void *,size_t),
    void (*)(void *),void (*)(void *),const Ops *,void (*)(void *,const void *,uint32_t),
    const void *,int *);

static pthread_mutex_t heap_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_rwlock_t vector_lock=PTHREAD_RWLOCK_INITIALIZER;
static thread_local unsigned line;
static const char token[]="native registry test";
static unsigned allocations,fail;
static uintptr_t read_word(const void *p) { uintptr_t v; std::memcpy(&v,p,8); return v; }
static void take(void *) { if (pthread_mutex_lock(&heap_lock)) std::abort(); }
static void drop(void *) { if (pthread_mutex_unlock(&heap_lock)) std::abort(); }
static int ready(void *) { return 1; }
static int init(void *) { std::abort(); }
static void *alloc(void *p,size_t n) {
    if (++allocations==fail) return nullptr;
    return bb_engine_regular_heap_allocate_02485730(static_cast<engine::regular_heap::Heap *>(p),n);
}
static void *aligned(void *p,size_t n,size_t a) {
    assert(n==0x28 && a==8);
    auto *owner=static_cast<unsigned char *>(p)-0x458;
    take(nullptr); void *r=alloc(owner,n); drop(nullptr); return r;
}
static int lock(void *) { assert(line==0xfb); return pthread_rwlock_wrlock(&vector_lock); }
static int unlock(void *) { return pthread_rwlock_unlock(&vector_lock); }
static void context(void *,const void *source,uint32_t n) { assert(source==token); line=n; }
static void overlap(void *) { std::abort(); }
static Area *grow(void *,size_t) { std::abort(); }
static void release(void *,Area *) { std::abort(); }

int main() {
    const Ops ops{nullptr,lock,unlock,overlap,grow,release};
    auto *arena=static_cast<unsigned char *>(std::malloc(0x100000));
    assert(arena);
    for (fail=0;fail<3;++fail) {
        alignas(16) unsigned char owner[0x490]{};
        uintptr_t p=reinterpret_cast<uintptr_t>(owner),a=reinterpret_cast<uintptr_t>(arena);
        std::memcpy(owner+0x460,&p,8); std::memset(arena,0xa5,0x100000);
        line=allocations=0; int status=99;
        auto *result=bb_registry_factory_cold_v595(owner,sizeof owner,arena,0x100000,
            ready,init,aligned,alloc,take,drop,&ops,context,token,&status);
        if (fail) { assert(!result && status==-3 && !line && allocations==fail); continue; }
        assert(result==owner && status==1 && line==0xfb && allocations==2);
        auto *meta=reinterpret_cast<const unsigned char *>(read_word(owner+0x468));
        auto *entry=reinterpret_cast<const unsigned char *>(read_word(meta+8));
        assert(read_word(meta+0x10)==reinterpret_cast<uintptr_t>(entry)+24);
        assert(read_word(meta+0x18)==reinterpret_cast<uintptr_t>(entry)+768);
        assert(read_word(entry)==p+0x458 && read_word(entry+8)==a && read_word(entry+16)==a+0x100000);
        assert(read_word(owner+0x20)==2);
    }
    std::free(arena);
    std::puts("V595 cold factory: native heap, two host locks, one registered area");
}
