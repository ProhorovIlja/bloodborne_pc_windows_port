/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_ctor_v578.h"
#include "native_direct_memory_host_v411.h"
#include "native_startup_mutex_v413.h"
#include "singleton_ctor_v576.h"
#include <stdio.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"V578:%d\n",__LINE__); return 1; } } while (0)
struct fixture {
    ShytStartupMutexV413 outer, inner;
    struct bb_arena_binding_v578 binding;
    enum bb_arena_result_v578 result;
    int deny_map;
    unsigned builds, locks, unlocks;
};
static int acquire(void *ctx,unsigned char *g) { (void)ctx; return !*g; }
static void release(void *ctx,unsigned char *g) { (void)ctx; *g=1; }
static unsigned char probe(void *ctx,unsigned char *obj) { (void)ctx; return obj[16]; }
static int outer_init(void *ctx,unsigned char *slot) {
    struct fixture *f=ctx;
    bb_arena_qword_v577(slot,1);
    return !shyt_startup_mutex_init_v413(&f->outer,2);
}
static int inner_init(void *ctx,unsigned char *slot) {
    struct fixture *f=ctx;
    bb_arena_qword_v577(slot,2);
    return !shyt_startup_mutex_init_v413(&f->inner,2);
}
static int lock(void *ctx,unsigned char *obj,int32_t timeout) {
    struct fixture *f=ctx;
    ++f->locks;
    return obj[16] && timeout==-1 && shyt_startup_mutex_lock_v413(&f->outer);
}
static int unlock(void *ctx,unsigned char *obj) {
    struct fixture *f=ctx;
    ++f->unlocks;
    return obj[16] && shyt_startup_mutex_unlock_v413(&f->outer);
}
static int construct(void *ctx,unsigned char *obj,size_t n) {
    struct fixture *f=ctx;
    ++f->builds;
    f->result=bb_arena_ctor_v578(obj,n,&f->binding);
    return f->result==BB_ARENA_OK;
}
static void *map(void *ctx,uint64_t off,uint64_t n,uint64_t a,int t,unsigned p) {
    const struct fixture *f=ctx;
    return f->deny_map ? NULL : shyt_dm_cpu_map(NULL,off,n,a,t,p);
}
int main(void) {
    const uint64_t n=BB_ARENA_SIZE_V577, a=BB_ARENA_ALIGN_V577;
    const struct bb_singleton_v576 x={{0,24,25,1},32,64,BB_ARENA_OBJECT_V577,40};
    const struct bb_singleton_calls_v576 calls={{acquire,release,probe,outer_init},lock,unlock,construct};
    for (unsigned mode=0;mode<3;++mode) {
        struct fixture f={0};
        _Alignas(8) unsigned char data[64+BB_ARENA_OBJECT_V577]={0};
        ShytDmPool pool={0};
        uint64_t first;
        CHECK(shyt_dm_init(&pool,mode==1 ? n : n+a));
        CHECK(shyt_dm_allocate(&pool,0,(int64_t)pool.limit,SHYT_DM_PAGE,0,0,&first)==SHYT_DM_OK);
        const ShytDmBackend backend={&f,map,shyt_dm_cpu_unmap};
        f.deny_map=(mode==2);
        f.binding=(struct bb_arena_binding_v578){&pool,&backend,2,3,inner_init,&f};
        const enum bb_singleton_result_v576 result=bb_singleton_ctor_v576(data,sizeof data,x,&calls,&f);
        uintptr_t published=0;
        memcpy(&published,data+32,8);
        CHECK(f.builds==1 && f.locks==1 && f.unlocks==1);
        if (!mode) {
            CHECK(result==BB_SINGLETON_OK && published==(uintptr_t)(data+64));
            CHECK(pool.count==2 && pool.blocks[1].offset==a && pool.blocks[1].mapping);
            CHECK(bb_singleton_ctor_v576(data,sizeof data,x,&calls,&f)==BB_SINGLETON_OK);
            CHECK(f.builds==1 && f.locks==1 && f.unlocks==1);
            CHECK(shyt_dm_release(&pool,a,n)==SHYT_DM_OK);
        } else {
            CHECK(result==BB_SINGLETON_STOP && !published && pool.count==1);
            CHECK(f.result==(mode==1 ? BB_ARENA_ALLOC : BB_ARENA_MAP));
        }
        CHECK(shyt_dm_release(&pool,first,SHYT_DM_PAGE)==SHYT_DM_OK && !pool.count);
        CHECK(shyt_startup_mutex_destroy_v413(&f.inner));
        CHECK(shyt_startup_mutex_destroy_v413(&f.outer));
    }
    return 0;
}
