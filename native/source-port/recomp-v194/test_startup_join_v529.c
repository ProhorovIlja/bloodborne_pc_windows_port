/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "singleton_v525.h"
#include "singleton_arena_v528.h"
#include "native_direct_memory_host_v411.h"
#include "mutex_host_v523.h"
#include "init_walk_v520.h"
#include <stdio.h>

enum { OBJ=128, BITMAP=40, MAP_FIELDS=1128 };
static const uint64_t base=0x100000, arena=0x80000000, bytes=0x7400000, align=0x200000;
static const struct bb_ctor_route_v524 route={
    .base=0x100000,.vtable=19,.guard=24,.done=25,.storage=32
};
static const struct bb_singleton_v525 singleton={0,OBJ,8,16,11,12};
struct fixture {
    unsigned char rw[OBJ+1200];
    struct bb_mutex_slot_v523 outer, inner;
    ShytDmPool pool;
    ShytDmBackend backend;
    struct bb_singleton_memory_v526 map;
    enum bb_arena_status_v528 status;
    unsigned locked, unlocked, inits, rejected;
};
static int make_mutex(struct bb_mutex_slot_v523 *s,uint64_t addr) {
    struct bb_mutex_result_v522 r=bb_mutex_host_v523(s,addr);
    return r.status==BB_MUTEX_RETURN_V522 && !r.value;
}
static const size_t inner_guard=56;
static int guard(void *x,enum bb_hook_v521 op,uint64_t addr,uint32_t *r) {
    struct fixture *s=x;
    if (addr!=base+inner_guard || s->locked!=1 || s->unlocked || s->inits) return 0;
    if (op==BB_ACQUIRE_V521 && !s->rw[57]) {
        s->rw[57]=1; *r=1; return 1;
    }
    if (op==BB_RELEASE_V521 && s->rw[57]==1) {
        s->rw[57]=2; s->rw[inner_guard]=1; return 1;
    }
    return 0;
}
static int sync_mutex(void *x,uint64_t id,uint64_t addr,uint32_t timeout) {
    struct fixture *s=x;
    if (addr+8!=s->outer.key) return 0;
    if (id==11 && timeout==UINT32_MAX && !pthread_mutex_lock(&s->outer.mutex)) {
        ++s->locked; return 1;
    }
    if (id==12 && !timeout && !pthread_mutex_unlock(&s->outer.mutex)) {
        ++s->unlocked; return 1;
    }
    return 0;
}
static int init_arena(void *x,uint64_t obj) {
    struct fixture *s=x;
    if (s->locked!=1 || s->unlocked || obj!=base+OBJ || bb_read64_v524(s->rw)) return 0;
    ++s->inits;
    unsigned char *p=s->rw+OBJ;
    bb_arena_store_v527(p,20);
    bb_arena_store_v527(p+8,obj);
    bb_arena_store_v527(p+16,21);
    memset(p+BITMAP,0,1120);
    if (!make_mutex(&s->inner,obj+24)) return 0;
    p[32]=1;
    s->status=bb_singleton_arena_v528(&s->pool,&s->backend,p,1200,BITMAP,MAP_FIELDS,
        obj,arena,bytes,align,&s->map);
    return s->status==BB_ARENA_READY;
}
static int read_slot(void *x,size_t off,uint64_t *v) {
    (void)x;
    switch (off) {
    case 32: *v=0; break;
    case 24: *v=1; break;
    case 16: *v=2; break;
    case 8: *v=3; break;
    default: return 0;
    }
    return 1;
}
static int invoke(void *x,uint64_t target) {
    struct fixture *s=x;
    if (target==1) {
        if (!make_mutex(&s->outer,base+40)) return 0;
        s->rw[24]=s->rw[25]=s->rw[48]=1;
        bb_arena_store_v527(s->rw+32,19);
        return 1;
    }
    if (target!=2) return 0;
    uint64_t out=0;
    return bb_singleton_guarded_v530(s->rw,sizeof s->rw,&route,&singleton,guard,
        sync_mutex,init_arena,s,&out,&inner_guard)==BB_SINGLETON_OK && out==base+OBJ;
}
static void *reject(void *x,uint64_t off,uint64_t n,uint64_t a,int t,unsigned p) {
    struct fixture *s=x;
    if (s->locked==1 && !s->unlocked && !off && n==bytes && a==align && !t && p==3)
        ++s->rejected;
    return NULL;
}
static void *check_unlocked(void *x) {
    struct fixture *s=x;
    if (pthread_mutex_trylock(&s->outer.mutex)) return NULL;
    return pthread_mutex_unlock(&s->outer.mutex)?NULL:x;
}
static int check(unsigned mode) {
    struct fixture s={0};
    bb_arena_store_v527(s.rw+8,11);
    bb_arena_store_v527(s.rw+16,12);
    s.backend=(ShytDmBackend){&s,mode==1?reject:shyt_dm_cpu_map,shyt_dm_cpu_unmap};
    if (!shyt_dm_init(&s.pool,mode==2?align:bytes+align)) return 1;
    struct bb_init_result_v520 r=bb_init_walk_v520(&s,read_slot,invoke,0,0,32,24,8);
    if (r.status!=BB_INIT_MISS_V520 || r.calls!=(mode?1u:2u) ||
        r.slot!=(mode?16u:8u) || s.locked!=1 || s.unlocked!=1 || s.inits!=1 || s.rw[57]!=2) return 2;
    pthread_t t;
    void *result=NULL;
    if (pthread_create(&t,NULL,check_unlocked,&s) || pthread_join(t,&result) || result!=&s) return 3;
    if (mode) {
        if (s.pool.count || s.map.storage || bb_read64_v524(s.rw) ||
            s.rejected!=(mode==1?1u:0u) ||
            s.status!=(mode==1?BB_ARENA_MAP:BB_ARENA_ALLOC)) return 4;
    } else {
        uint64_t out=0;
        if (s.status!=BB_ARENA_READY || s.pool.count!=1 || !s.map.storage ||
            s.map.offset || bb_read64_v524(s.rw+OBJ+MAP_FIELDS)!=arena ||
            bb_read64_v524(s.rw)!=base+OBJ ||
            bb_singleton_guarded_v530(s.rw,sizeof s.rw,&route,&singleton,guard,
                sync_mutex,init_arena,&s,&out,&inner_guard)!=BB_SINGLETON_OK ||
            out!=base+OBJ || s.locked!=1 || s.inits!=1) return 5;
        if (shyt_dm_release(&s.pool,s.map.offset,bytes)!=SHYT_DM_OK || s.pool.count) return 6;
    }
    return pthread_mutex_destroy(&s.inner.mutex) || pthread_mutex_destroy(&s.outer.mutex);
}
int main(void) {
    for (unsigned mode=0;mode<3;++mode) {
        const int result=check(mode);
        if (result) return (int)(10*mode)+result;
    }
    puts("V529_STARTUP_JOIN_PASS");
    return 0;
}
