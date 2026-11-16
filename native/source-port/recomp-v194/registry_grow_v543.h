/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_GROW_V543_H
#define BB_REGISTRY_GROW_V543_H
#include "registry_insert_v542.h"

struct bb_growth_v543 {
    void *ctx;
    int (*allocate)(void *,uint64_t,size_t,struct bb_vector_block_v541 *);
    int (*release)(void *,uint64_t,uint64_t);
};
/* Caller serializes registry writes. Allocator hooks own their lock and
 * supply disjoint host buffers. Failure is terminal, not a retry contract. */
static inline enum bb_insert_v542 bb_registry_grow_v543(unsigned char *h,
        size_t size,uint64_t hva,const struct bb_vector_block_v541 *old,
        uint64_t key,uint64_t first,uint64_t extent,int (*warn)(void *),
        void *warn_ctx,const struct bb_growth_v543 *g) {
    if (!h || size<40 || !hva || hva>UINT64_MAX-40 || !old || !g ||
        !g->allocate || !g->release) return BB_INSERT_INVALID;
    const uint64_t lo=bb_vector_word_v541(h+8), hi=bb_vector_word_v541(h+16),
        cap=bb_vector_word_v541(h+24), owner=bb_vector_word_v541(h+32);
    if (!owner || (lo<hva+40 && hva<cap)) return BB_INSERT_INVALID;
    size_t pos=0;
    enum bb_insert_v542 r=bb_registry_insert_route_v543(h,size,old,key,first,
        extent,warn,warn_ctx,&pos);
    if (r!=BB_INSERT_FULL) return r;
    const size_t used=(size_t)(hi-lo), count=used/24, max=SIZE_MAX/24;
    if (count>=max) return BB_INSERT_STOP;
    const size_t grown=count/2>max-count?count+1:count+count/2;
    const size_t bytes=24*(grown>count?grown:count+1);
    struct bb_vector_block_v541 b={0};
    if (!g->allocate(g->ctx,owner,bytes,&b) || !b.data || b.size<bytes ||
        !b.va || (b.va&7) || b.va>UINT64_MAX-bytes || b.va==lo ||
        (b.va<cap && lo<b.va+bytes) || (b.va<hva+40 && hva<b.va+bytes))
        return BB_INSERT_STOP;
    memcpy(b.data,old->data,pos);
    bb_arena_store_v527(b.data+pos,key);
    bb_arena_store_v527(b.data+pos+8,first);
    bb_arena_store_v527(b.data+pos+16,first+extent);
    memcpy(b.data+pos+24,old->data+pos,used-pos);
    if (!g->release(g->ctx,owner,lo)) return BB_INSERT_STOP;
    bb_arena_store_v527(h+24,b.va+bytes);
    bb_arena_store_v527(h+16,b.va+used+24);
    bb_arena_store_v527(h+8,b.va);
    return BB_INSERT_OK;
}
#endif
