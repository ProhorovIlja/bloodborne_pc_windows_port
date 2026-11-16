/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "owner_registry_v540.h"
#include "registry_grow_v543.h"
#include <errno.h>

/* Test only: descriptors and heap links use identity addresses in this
 * process. This is not an adapter for the runtime's guest VA aperture. */
extern void *bb_engine_regular_heap_allocate_aligned_02485a60(void *,uint64_t,uint64_t);
extern void bb_engine_regular_heap_free_024858a0(void *,void *);
static _Alignas(16) unsigned char arena[0x100000];
struct locked_heap {
    unsigned char *body;
    ShytStartupRwlockV414 *registry;
    pthread_mutex_t mutex;
    unsigned calls;
};
struct probe { struct locked_heap *heap; int writer, allocator, ok; };
static void *probe_thread(void *ctx) {
    struct probe *p=ctx;
    int r=pthread_rwlock_tryrdlock(&p->heap->registry->os);
    int m=pthread_mutex_trylock(&p->heap->mutex);
    p->ok=(r==(p->writer?EBUSY:0) && m==(p->allocator?EBUSY:0));
    if (!m && pthread_mutex_unlock(&p->heap->mutex)) p->ok=0;
    if (!r && pthread_rwlock_unlock(&p->heap->registry->os)) p->ok=0;
    return NULL;
}
static int probe(struct locked_heap *h,int writer,int allocator) {
    struct probe p={h,writer,allocator,0}; pthread_t t;
    return !pthread_create(&t,NULL,probe_thread,&p) && !pthread_join(t,NULL) && p.ok;
}
static int enter(struct locked_heap *h) {
    if (pthread_mutex_lock(&h->mutex)) return 0;
    ++h->calls;
    if (probe(h,h->registry->held!=0,1)) return 1;
    (void)pthread_mutex_unlock(&h->mutex);
    return 0;
}
static int get(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    struct locked_heap *h=x;
    if (owner!=(uintptr_t)h->body || !enter(h)) return 0;
    void *p=bb_engine_regular_heap_allocate_aligned_02485a60(h->body,n,8);
    *b=(struct bb_vector_block_v541){p,n,(uintptr_t)p};
    return !pthread_mutex_unlock(&h->mutex) && p!=NULL;
}
static int put(void *x,uint64_t owner,uint64_t va) {
    struct locked_heap *h=x;
    if (owner!=(uintptr_t)h->body || !va || !enter(h)) return 0;
    bb_engine_regular_heap_free_024858a0(h->body,(void *)(uintptr_t)va);
    return !pthread_mutex_unlock(&h->mutex);
}
static int make_header(void *x,uint64_t self,size_t n,size_t alignment,struct bb_registry_block_v540 *b) {
    struct locked_heap *h=x;
    struct bb_vector_block_v541 r;
    if (self!=(uintptr_t)h->body+0x458 || alignment!=8 || !get(x,(uintptr_t)h->body,n,&r)) return 0;
    *b=(struct bb_registry_block_v540){r.data,r.size,r.va};
    return 1;
}
static int warn(void *x) { (void)x; return 0; }
int main(void) {
    struct bb_owner_v539 owner={0};
    _Alignas(16) unsigned char body[0x490]={0}; unsigned char once=0;
    struct locked_heap heap={body,&owner.lock,PTHREAD_MUTEX_INITIALIZER,0};
    if (!bb_owner_seed_v539(&owner,body,sizeof body,(uintptr_t)body,1,2,3) ||
        bb_owner_registry_v540(&owner,(uintptr_t)body,&once,arena,(uintptr_t)arena,
            &heap,make_header)!=BB_REGISTRY_SEEDED) return 1;
    const uint64_t hva=bb_vector_word_v541(body+0x468);
    unsigned char *h=(unsigned char *)(uintptr_t)hva;
    if (bb_vector_reserve_v541(h,40,hva,NULL,&heap,get,put)!=BB_VEC_READY) return 2;
    const struct bb_growth_v543 g={&heap,get,put};
    for (unsigned i=0;i<65;++i) {
        const uint64_t lo=bb_vector_word_v541(h+8), cap=bb_vector_word_v541(h+24);
        const struct bb_vector_block_v541 b={(unsigned char *)(uintptr_t)lo,(size_t)(cap-lo),lo};
        if (!shyt_rw_write_v414(&owner.lock)) return 7;
        if (bb_registry_grow_v543(h,40,hva,&b,1+i,0x2000+32*i,16,warn,NULL,&g)!=BB_INSERT_OK)
            return 3;
        if (!shyt_rw_unlock_v414(&owner.lock)) return 8;
    }
    const uint64_t lo=bb_vector_word_v541(h+8);
    if (bb_vector_word_v541(h+16)-lo!=65*24 || bb_vector_word_v541(h+24)-lo!=72*24) return 4;
    for (unsigned i=0;i<65;++i) {
        const unsigned char *p=(const unsigned char *)(uintptr_t)lo+24*i;
        if (bb_vector_word_v541(p)!=1+i || bb_vector_word_v541(p+8)!=0x2000+32*i ||
            bb_vector_word_v541(p+16)!=0x2010+32*i) return 5;
    }
    if (!put(&heap,(uintptr_t)body,lo) || !put(&heap,(uintptr_t)body,hva) ||
        heap.calls!=8 || !probe(&heap,0,0) || pthread_mutex_destroy(&heap.mutex) ||
        bb_vector_word_v541(body+32) || bb_vector_word_v541(body+24)!=bb_vector_word_v541(body+0x438) ||
        !shyt_rw_destroy_v414(&owner.lock)) return 6;
    return 0;
}
