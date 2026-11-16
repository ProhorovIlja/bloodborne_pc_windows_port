/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLASS_SECONDARY_V557_H
#define BB_CLASS_SECONDARY_V557_H
#include "class_sort_v556.h"

/* Experimental secondary table only; not wired to retail startup.
 * Caller holds registry lock, supplies disjoint host buffers and a growth
 * policy (the retail growth path is not yet verified). A failed release
 * must leave the target allocation live. STOP is terminal for the caller. */
enum bb_secondary_v557 { BB_SEC_INVALID, BB_SEC_STOP, BB_SEC_OK };
static inline enum bb_secondary_v557 bb_secondary_insert_v557(
        unsigned char *h,size_t n,uint64_t hva,const struct bb_vector_block_v541 *old,
        uint64_t cls,void *ctx,int (*key)(void *,uint64_t,unsigned,uint64_t *),
        size_t (*growth)(void *,size_t,size_t),
        int (*alloc)(void *,uint64_t,size_t,struct bb_vector_block_v541 *),
        int (*release)(void *,uint64_t,uint64_t)) {
    enum { stride=16, initial=512, batch=4 };
    if (!h || n<40 || !hva || hva>UINT64_MAX-40 || !cls || !key || !growth ||
        !alloc || !release) return BB_SEC_INVALID;
    const uint64_t lo=bb_vector_word_v541(h+8), hi=bb_vector_word_v541(h+16),
        cap=bb_vector_word_v541(h+24), owner=bb_vector_word_v541(h+32);
    if (!owner || lo>hi || hi>cap || ((lo|hi|cap)&7) ||
        ((hi-lo)|(cap-lo))%stride || (!lo && cap) ||
        (lo && (!old || !old->data || old->va!=lo || cap-lo>old->size ||
        (lo<hva+40 && hva<cap)))) return BB_SEC_INVALID;
    const size_t used=(size_t)((hi-lo)/stride), capacity=(size_t)((cap-lo)/stride);
    if (used>SIZE_MAX/stride-batch) return BB_SEC_STOP;
    const size_t total=used+batch;
    const size_t slots=!lo?initial:(total>capacity?growth(ctx,capacity,total):capacity);
    if (slots<total || slots>SIZE_MAX/stride) return BB_SEC_STOP;
    const size_t bytes=slots*stride;
    uint64_t keys[batch];
    for (unsigned i=0;i<batch;++i)
        if (!key(ctx,cls,i,&keys[i])) return BB_SEC_STOP;

    const int replace=!lo || slots!=capacity;
    struct bb_vector_block_v541 b={0};
    if (replace) {
        if (!alloc(ctx,owner,bytes,&b) || !b.data || b.size<bytes || !b.va ||
            (b.va&7) || b.va>UINT64_MAX-bytes || b.va==lo ||
            (b.va<hva+40 && hva<b.va+bytes) ||
            (lo && b.va<cap && lo<b.va+bytes)) return BB_SEC_STOP;
        if (used) memcpy(b.data,old->data,stride*used);
    } else b=*old;
    for (unsigned i=0;i<batch;++i) {
        unsigned char *row=b.data+stride*(used+i);
        bb_arena_store_v527(row,keys[i]);
        bb_arena_store_v527(row+8,cls);
    }
    if (!bb_class_sort_v556(b.data,bytes,total)) return BB_SEC_STOP;
    if (replace && lo && !release(ctx,owner,lo)) {
        (void)release(ctx,owner,b.va);
        return BB_SEC_STOP;
    }
    if (replace) {
        bb_arena_store_v527(h+24,b.va+bytes);
        bb_arena_store_v527(h+8,b.va);
    }
    bb_arena_store_v527(h+16,b.va+stride*total);
    return BB_SEC_OK;
}
#endif
