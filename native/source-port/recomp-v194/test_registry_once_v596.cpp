/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <pthread.h>
#include <thread>
#include <atomic>

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
struct Once { void *published; int terminal; };
struct Host {
    void *ctx;
    int (*lock)(void *),(*unlock)(void *),(*rw_init)(void *,void *);
    uintptr_t mutex_table,allocator_table,rw_table;
};
extern "C" void *bb_registry_once_v596(Once *,const Host *,unsigned char *,size_t,unsigned char *,size_t,
    int (*)(void *),int (*)(void *),void *(*)(void *,size_t,size_t),void *(*)(void *,size_t),
    void (*)(void *),void (*)(void *),const Ops *,void (*)(void *,const void *,uint32_t),const void *,int *);
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static unsigned inits;
static int enter(void *) { return pthread_mutex_lock(&gate); }
static int leave(void *) { return pthread_mutex_unlock(&gate); }
static int rw_init(void *,void *);
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

static int rw_init(void *,void *p) {
    ++inits;
    assert(read_word(p)==3 && static_cast<unsigned char *>(p)[0x10]==0);
    return fail==3;
}
int main() {
    const Ops ops{nullptr,lock,unlock,overlap,grow,release};
    const Host host{nullptr,enter,leave,rw_init,1,2,3};
    auto *arena=static_cast<unsigned char *>(std::malloc(0x100000));
    assert(arena);
    for (fail=0;fail<4;++fail) {
        alignas(16) unsigned char owner[0x490];
        std::memset(owner,0xa5,sizeof owner); std::memset(arena,0xa5,0x100000);
        const uintptr_t p=reinterpret_cast<uintptr_t>(owner),a=reinterpret_cast<uintptr_t>(arena);
        line=allocations=inits=0; Once once{};
        auto invoke=[&](int *status) { return bb_registry_once_v596(&once,&host,owner,sizeof owner,
            arena,0x100000,ready,init,aligned,alloc,take,drop,&ops,context,token,status); };
        if (fail) {
            int status=99;
            for (int i=0;i<4;++i) {
                assert(!invoke(&status) && status==(fail==3?-2:-3));
                assert(!once.published && inits==1 && !line && allocations==(fail==3?0:fail));
            }
            continue;
        }
        std::atomic<unsigned> arrived{0};
        std::thread threads[16];
        for (auto &t:threads) t=std::thread([&] {
            ++arrived; while (arrived.load()!=16) std::this_thread::yield();
            int status=99;
            assert(invoke(&status)==owner && status==1);
            const auto *m=reinterpret_cast<const unsigned char *>(read_word(owner+0x468));
            assert(read_word(m+0x10)==read_word(m+8)+24);
        });
        for (auto &t:threads) t.join();
        assert(once.published==owner && inits==1 && allocations==2);
        const auto *m=reinterpret_cast<const unsigned char *>(read_word(owner+0x468));
        const auto *entry=reinterpret_cast<const unsigned char *>(read_word(m+8));
        assert(read_word(m+0x18)==reinterpret_cast<uintptr_t>(entry)+768);
        assert(read_word(entry)==p+0x458 && read_word(entry+8)==a && read_word(entry+16)==a+0x100000);
        assert(read_word(owner+0x20)==2);
    }
    std::free(arena);
    std::puts("V596 factory: 16 concurrent calls, one publication; terminal failures not replayed");
}
