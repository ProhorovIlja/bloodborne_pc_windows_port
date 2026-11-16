/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "owner_registry_v540.h"
#include "registry_grow_v543.h"

/* Test only: descriptors and heap links use identity addresses in this
 * process. This is not an adapter for the runtime's guest VA aperture. */
extern void *bb_engine_regular_heap_allocate_aligned_02485a60(void *,uint64_t,uint64_t);
extern void bb_engine_regular_heap_free_024858a0(void *,void *);
static _Alignas(16) unsigned char arena[0x100000];
static int get(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    if (owner!=(uintptr_t)x) return 0;
    void *p=bb_engine_regular_heap_allocate_aligned_02485a60(x,n,8);
    *b=(struct bb_vector_block_v541){p,n,(uintptr_t)p};
    return p!=NULL;
}
static int put(void *x,uint64_t owner,uint64_t va) {
    if (owner!=(uintptr_t)x || !va) return 0;
    bb_engine_regular_heap_free_024858a0(x,(void *)(uintptr_t)va);
    return 1;
}
static int make_header(void *x,uint64_t self,size_t n,size_t alignment,struct bb_registry_block_v540 *b) {
    struct bb_vector_block_v541 r;
    if (self!=(uintptr_t)x+0x458 || alignment!=8 || !get(x,(uintptr_t)x,n,&r)) return 0;
    *b=(struct bb_registry_block_v540){r.data,r.size,r.va};
    return 1;
}
static int warn(void *x) { (void)x; return 0; }
int main(void) {
    struct bb_owner_v539 owner={0};
    _Alignas(16) unsigned char body[0x490]={0}; unsigned char once=0;
    if (!bb_owner_seed_v539(&owner,body,sizeof body,(uintptr_t)body,1,2,3) ||
        bb_owner_registry_v540(&owner,(uintptr_t)body,&once,arena,(uintptr_t)arena,
            body,make_header)!=BB_REGISTRY_SEEDED) return 1;
    const uint64_t hva=bb_vector_word_v541(body+0x468);
    unsigned char *h=(unsigned char *)(uintptr_t)hva;
    if (bb_vector_reserve_v541(h,40,hva,NULL,body,get,put)!=BB_VEC_READY) return 2;
    const struct bb_growth_v543 g={body,get,put};
    for (unsigned i=0;i<65;++i) {
        const uint64_t lo=bb_vector_word_v541(h+8), cap=bb_vector_word_v541(h+24);
        const struct bb_vector_block_v541 b={(unsigned char *)(uintptr_t)lo,(size_t)(cap-lo),lo};
        if (bb_registry_grow_v543(h,40,hva,&b,1+i,0x2000+32*i,16,warn,NULL,&g)!=BB_INSERT_OK)
            return 3;
    }
    const uint64_t lo=bb_vector_word_v541(h+8);
    if (bb_vector_word_v541(h+16)-lo!=65*24 || bb_vector_word_v541(h+24)-lo!=72*24) return 4;
    for (unsigned i=0;i<65;++i) {
        const unsigned char *p=(const unsigned char *)(uintptr_t)lo+24*i;
        if (bb_vector_word_v541(p)!=1+i || bb_vector_word_v541(p+8)!=0x2000+32*i ||
            bb_vector_word_v541(p+16)!=0x2010+32*i) return 5;
    }
    if (!put(body,(uintptr_t)body,lo) || !put(body,(uintptr_t)body,hva) ||
        bb_vector_word_v541(body+32) || bb_vector_word_v541(body+24)!=bb_vector_word_v541(body+0x438) ||
        !shyt_rw_destroy_v414(&owner.lock)) return 6;
    return 0;
}
