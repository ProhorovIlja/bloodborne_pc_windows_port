/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "owner_factory_v552.h"
#include "mutex_host_v523.h"

extern void *bb_engine_regular_heap_allocate_aligned_02485a60(void *,uint64_t,uint64_t);
extern void bb_engine_regular_heap_free_024858a0(void *,void *);
static _Alignas(16) unsigned char arena[0x100000];
/* Serialized test only. DLRegularHeap metadata is host-private; registry
 * references use the guest region. Free is only called with live blocks. */
struct fixture {
    struct bb_region_v478 span;
    uint64_t owner;
    unsigned char *body;
    struct bb_mutex_slot_v523 heap;
    uint64_t live[3];
    unsigned deny_reserve;
};
static enum bb_alloc_v548 get(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    struct fixture *f=x;
    if (owner!=f->owner || f->heap.key!=f->owner+0x448 || !n || pthread_mutex_lock(&f->heap.mutex)) return BB_ALLOC_ERROR;
    if (f->deny_reserve && n==768) {
        return pthread_mutex_unlock(&f->heap.mutex)?BB_ALLOC_ERROR:BB_ALLOC_NO_SPACE;
    }
    size_t slot=0;
    while (slot<3 && f->live[slot]) ++slot;
    if (slot==3) { (void)pthread_mutex_unlock(&f->heap.mutex); return BB_ALLOC_ERROR; }
    void *p=bb_engine_regular_heap_allocate_aligned_02485a60(f->body,n,8);
    if (!p) return pthread_mutex_unlock(&f->heap.mutex)?BB_ALLOC_ERROR:BB_ALLOC_NO_SPACE;
    const uintptr_t addr=(uintptr_t)p, base=(uintptr_t)f->span.data;
    if (addr<base || n>f->span.size || addr-base>f->span.size-n) {
        (void)pthread_mutex_unlock(&f->heap.mutex);
        return BB_ALLOC_ERROR;
    }
    *out=(struct bb_vector_block_v541){p,n,f->span.base+(addr-base)};
    f->live[slot]=out->va;
    return pthread_mutex_unlock(&f->heap.mutex)?BB_ALLOC_ERROR:BB_ALLOC_OK;
}
static int put(void *x,uint64_t owner,uint64_t va) {
    struct fixture *f=x;
    unsigned char *p=bb_memory_at_v478(&f->span,va,1);
    if (owner!=f->owner || f->heap.key!=f->owner+0x448 || !p || (va&15) || pthread_mutex_lock(&f->heap.mutex)) return 0;
    size_t slot=0;
    while (slot<3 && f->live[slot]!=va) ++slot;
    if (slot==3) { (void)pthread_mutex_unlock(&f->heap.mutex); return 0; }
    bb_engine_regular_heap_free_024858a0(f->body,p);
    f->live[slot]=0;
    return !pthread_mutex_unlock(&f->heap.mutex);
}
static int header(void *x,uint64_t self,size_t n,size_t align,struct bb_registry_block_v540 *out) {
    struct fixture *f=x; struct bb_vector_block_v541 b;
    if (self!=f->owner+0x458 || align!=8 || get(x,f->owner,n,&b)!=BB_ALLOC_OK) return 0;
    *out=(struct bb_registry_block_v540){b.data,b.size,b.va};
    return 1;
}
static int warn(void *x) { (void)x; return 0; }
/* Bind serialized startup callbacks to host synchronization without using
 * guest memory as a pthread object. The two guards are not general cxa guards. */
struct cold_fixture {
    struct fixture *heap;
    struct bb_owner_v539 *owner;
    unsigned char rw[128];
    uint64_t base;
    struct bb_mutex_slot_v523 publication;
    unsigned pending, locked, events;
};
static int init_slot(struct bb_mutex_slot_v523 *s,uint64_t va) {
    const struct bb_mutex_result_v522 r=bb_mutex_host_v523(s,va);
    return r.status==BB_MUTEX_RETURN_V522 && !r.value;
}
static int init_heap(struct fixture *f,uint64_t va) {
    if (va!=f->owner+0x448 || !init_slot(&f->heap,va)) return 0;
    bb_arena_store_v527(f->body+0x448,UINT64_C(0x55300002));
    f->body[0x450]=1;
    return 1;
}
static int guard(void *x,enum bb_hook_v521 op,uint64_t va,uint32_t *out) {
    struct cold_fixture *c=x;
    ++c->events;
    if (op==BB_ACQUIRE_V521 || op==BB_RELEASE_V521) {
        const unsigned which=va==c->base?1u:va==c->base+2?2u:0u;
        if (!which || c->locked!=(which==2)) return 0;
        unsigned char *b=c->rw+(which-1)*2;
        if (op==BB_ACQUIRE_V521) {
            if (c->pending || *b) return 0;
            c->pending=which; *out=1;
        } else {
            if (c->pending!=which || *b) return 0;
            *b=1; c->pending=0; *out=0;
        }
        return 1;
    }
    if (c->pending || c->locked || !c->rw[0]) return 0;
    if (op==BB_TEST_V521 && va==c->base+16) {
        *out=c->publication.key==va+8;
        return 1;
    }
    if (op!=BB_INIT_V521 || va!=c->base+24 || !init_slot(&c->publication,va)) return 0;
    bb_arena_store_v527(c->rw+24,UINT64_C(0x55300001));
    *out=0;
    return 1;
}
static int sync_owner(void *x,uint64_t id,uint64_t va,uint32_t timeout) {
    struct cold_fixture *c=x;
    ++c->events;
    if (va!=c->base+16 || c->publication.key!=va+8 || c->pending) return 0;
    if (id==4 && timeout==UINT32_MAX && !c->locked) {
        if (pthread_mutex_lock(&c->publication.mutex)) return 0;
        c->locked=1;
        return 1;
    }
    if (id!=5 || timeout || !c->locked || pthread_mutex_unlock(&c->publication.mutex)) return 0;
    c->locked=0;
    return 1;
}
static int seed_owner(void *x,uint64_t va) {
    struct cold_fixture *c=x;
    ++c->events;
    return c->locked && c->rw[2] && va==c->heap->owner && !bb_read64_v524(c->rw+48) &&
        bb_owner_seed_v539(c->owner,c->heap->body,0x490,va,1,2,3);
}
static int heap_after_publication(void *x,uint64_t va) {
    struct cold_fixture *c=x;
    ++c->events;
    if (c->locked || bb_read64_v524(c->rw+48)!=c->heap->owner ||
        pthread_mutex_trylock(&c->publication.mutex)) return 0;
    if (pthread_mutex_unlock(&c->publication.mutex)) return 0;
    return init_heap(c->heap,va);
}
static int run(uint64_t base,int mode) {
    _Alignas(16) unsigned char body[0x490]={0}; unsigned char once=0,tls[80]={0};
    struct bb_owner_v539 owner={0};
    struct fixture f={.span={base,sizeof arena,arena},.owner=base+0x200040,.body=body,.deny_reserve=mode==2};
    const struct bb_registry_tls_v548 t={tls,sizeof tls,48,base+0x300000,0x9999,-24,-8,-48};
    const struct bb_registry_driver_v548 d={&f,get,put};
    if (mode) {
        struct cold_fixture c={.heap=&f,.owner=&owner,.base=f.owner-64};
        struct bb_owner_factory_v552 factory={0};
        const struct bb_ctor_route_v524 p={.base=c.base,.guard=0,.done=1,.storage=16,.vtable=6};
        const struct bb_singleton_v525 k={48,64,32,40,4,5};
        bb_arena_store_v527(c.rw+32,4); bb_arena_store_v527(c.rw+40,5);
        uint64_t out=99;
        if (bb_owner_factory_v552(&factory,&owner,c.rw,sizeof c.rw,&p,&k,2,guard,sync_owner,seed_owner,
                heap_after_publication,&c,&f.span,(uintptr_t)body,(uintptr_t)arena,&t,&d,header,warn,&out)!=(mode==1) ||
            out!=(mode==1?f.owner:99) || c.events!=10 || c.locked || c.pending ||
            bb_read64_v524(c.rw+48)!=f.owner || factory.finish.once!=1 ||
            tls[32]!=(mode==2?0:0xfb)) return 9;
        unsigned char before[sizeof body]; memcpy(before,body,sizeof body);
        f.deny_reserve=0; tls[32]=0x42; out=99;
        if (bb_owner_factory_v552(&factory,&owner,c.rw,sizeof c.rw,&p,&k,2,guard,sync_owner,seed_owner,
                heap_after_publication,&c,&f.span,(uintptr_t)body,(uintptr_t)arena,&t,&d,header,warn,&out)!=(mode==1) ||
            out!=(mode==1?f.owner:99) || c.events!=10 || memcmp(before,body,sizeof body) ||
            tls[32]!=0x42 || pthread_mutex_destroy(&c.publication.mutex)) return 10;
        if (mode==2) {
            const uint64_t h=bb_vector_word_v541(body+0x468);
            if (!h || !put(&f,f.owner,h) || bb_vector_word_v541(body+32) ||
                pthread_mutex_destroy(&f.heap.mutex) || !shyt_rw_destroy_v414(&owner.lock)) return 11;
            return 0;
        }
    } else if (!bb_owner_seed_v539(&owner,body,sizeof body,f.owner,1,2,3) ||
        !init_heap(&f,f.owner+0x448) ||
        bb_owner_registry_seed_v549(&owner,f.owner,(uintptr_t)body,&once,arena,(uintptr_t)arena,&f,header)!=BB_REGISTRY_SEEDED) return 1;
    const uint64_t hva=bb_vector_word_v541(body+0x468);
    unsigned char *h=bb_memory_at_v478(&f.span,hva,40);
    if (!h || (uintptr_t)h==hva || bb_vector_word_v541(h+32)!=f.owner ||
        bb_memory_at_v478(&f.span,base-1,1) || bb_memory_at_v478(&f.span,base+sizeof arena-1,2) ||
        put(&f,f.owner,base+sizeof arena)) return 2;
    if (mode) {
        const uint64_t first=bb_vector_word_v541(h+8);
        const unsigned char *r=bb_memory_at_v478(&f.span,first,24);
        if (!r || bb_vector_word_v541(h+16)!=first+24 || bb_vector_word_v541(h+24)!=first+768 ||
            bb_vector_word_v541(r)!=f.owner+0x458 || bb_vector_word_v541(r+8)!=base ||
            bb_vector_word_v541(r+16)!=base+sizeof arena) return 3;
    }
    for (unsigned i=0;i<65;++i) {
        const uint64_t lo=bb_vector_word_v541(h+8), cap=bb_vector_word_v541(h+24);
        struct bb_vector_block_v541 b={bb_memory_at_v478(&f.span,lo,(size_t)(cap-lo)),(size_t)(cap-lo),lo};
        const struct bb_registry_result_v548 r=bb_registry_startup_v548(&owner.lock,&t,h,40,hva,
            lo?&b:NULL,1+i,0x2000+32*i,16,warn,NULL,&d);
        if (!r.unlocked || r.insert!=BB_INSERT_OK || r.action.kind!=BB_TX_INVALID || tls[32]!=0xfb) return 4;
    }
    const uint64_t lo=bb_vector_word_v541(h+8), cap=bb_vector_word_v541(h+24);
    const unsigned char *p=bb_memory_at_v478(&f.span,lo,(size_t)(cap-lo));
    if (!p || (uintptr_t)p==lo || bb_vector_word_v541(h+16)-lo!=(65u+(mode!=0))*24 ||
        (cap-lo)!=(mode?72u:94u)*24) return 5;
    for (unsigned i=0;i<65;++i,p+=24) {
        if (bb_vector_word_v541(p)!=1+i || bb_vector_word_v541(p+8)!=0x2000+32*i ||
            bb_vector_word_v541(p+16)!=0x2010+32*i) return 6;
    }
    if (mode && (bb_vector_word_v541(p)!=f.owner+0x458 || bb_vector_word_v541(p+8)!=base)) return 12;
    if (put(&f,f.owner,lo+16) || put(&f,f.owner+16,lo)) return 8;
    if (!put(&f,f.owner,lo) || !put(&f,f.owner,hva) ||
        put(&f,f.owner,lo) || put(&f,f.owner,hva) || bb_vector_word_v541(body+32) ||
        bb_vector_word_v541(body+24)!=bb_vector_word_v541(body+0x438) ||
        pthread_mutex_destroy(&f.heap.mutex) || !shyt_rw_destroy_v414(&owner.lock)) return 7;
    return 0;
}
int main(void) {
    const uint64_t base[]={0x100000,0x100000000,UINT64_C(0x7fff00000000)};
    for (unsigned i=0;i<sizeof base/sizeof *base;++i)
        for (int p=0;p<3;++p) { int r=run(base[i],p); if (r) return r; }
    return 0;
}
