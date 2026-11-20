/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLASS_SECONDARY_V557_H
#define BB_CLASS_SECONDARY_V557_H
#include "class_sort_v556.h"

/* Experimental secondary table; caller owns locking and disjoint host
 * buffers. STOP is terminal: reserve or earlier appends may be visible.
 * Allocation callback must return an 8-byte-aligned guest address.
 * Failed release must leave its target live. */
enum bb_secondary_v557 { BB_SEC_INVALID, BB_SEC_STOP, BB_SEC_OK };
static inline size_t bb_secondary_slots_v559(size_t n) {
    const size_t max=SIZE_MAX/16;
    if (n>=max) return 0;
    return n/2<=max-n && n/2 ? n+n/2 : n+1;
}
static inline int bb_secondary_resize_v559(unsigned char *h,uint64_t hva,
        uint64_t owner,struct bb_vector_block_v541 *live,size_t used,size_t capacity,
        size_t slots,void *ctx,
        int (*alloc)(void *,uint64_t,size_t,struct bb_vector_block_v541 *),
        int (*release)(void *,uint64_t,uint64_t)) {
    const size_t bytes=slots*16;
    struct bb_vector_block_v541 b={0};
    if (!alloc(ctx,owner,bytes,&b) || !b.data || b.size<bytes || !b.va ||
        (b.va&7) || b.va>UINT64_MAX-bytes || b.va==live->va ||
        (b.va<hva+40 && hva<b.va+bytes) ||
        (live->va && b.va<live->va+capacity*16 && live->va<b.va+bytes)) return 0;
    if (used) memcpy(b.data,live->data,used*16);
    if (live->va && !release(ctx,owner,live->va)) {
        (void)release(ctx,owner,b.va);
        return 0;
    }
    *live=b;
    bb_arena_store_v527(h+24,b.va+bytes);
    bb_arena_store_v527(h+16,b.va+used*16);
    bb_arena_store_v527(h+8,b.va);
    return 1;
}
static inline enum bb_secondary_v557 bb_secondary_insert_v557(
        unsigned char *h,size_t n,uint64_t hva,const struct bb_vector_block_v541 *old,
        uint64_t cls,void *ctx,int (*key)(void *,uint64_t,unsigned,uint64_t *),
        int (*alloc)(void *,uint64_t,size_t,struct bb_vector_block_v541 *),
        int (*release)(void *,uint64_t,uint64_t)) {
    enum { stride=16, initial=512, batch=4 };
    if (!h || n<40 || !hva || hva>UINT64_MAX-40 || !cls || !key ||
        !alloc || !release) return BB_SEC_INVALID;
    const uint64_t lo=bb_vector_word_v541(h+8), hi=bb_vector_word_v541(h+16),
        cap=bb_vector_word_v541(h+24), owner=bb_vector_word_v541(h+32);
    if (!owner || lo>hi || hi>cap || ((lo|hi|cap)&7) ||
        ((hi-lo)|(cap-lo))%stride || (!lo && cap) ||
        (lo && (!old || !old->data || old->va!=lo || cap-lo>old->size ||
        (lo<hva+40 && hva<cap)))) return BB_SEC_INVALID;
    size_t used=(size_t)((hi-lo)/stride), capacity=(size_t)((cap-lo)/stride);
    if (used>SIZE_MAX/stride-batch) return BB_SEC_STOP;
    struct bb_vector_block_v541 live={0};
    if (lo) live=*old;
    /* Retail reserves the cold vector before reading any class key. */
    if (!used && capacity<initial) {
        if (!bb_secondary_resize_v559(h,hva,owner,&live,used,capacity,initial,
                ctx,alloc,release)) return BB_SEC_STOP;
        capacity=initial;
    }
    uint64_t keys[batch];
    for (unsigned i=0;i<batch;++i)
        if (!key(ctx,cls,i,&keys[i])) return BB_SEC_STOP;
    /* Append one row at a time; grow at the first full-vector append. */
    for (unsigned i=0;i<batch;++i) {
        if (used==capacity) {
            const size_t slots=bb_secondary_slots_v559(capacity);
            if (!slots || !bb_secondary_resize_v559(h,hva,owner,&live,used,capacity,
                    slots,ctx,alloc,release)) return BB_SEC_STOP;
            capacity=slots;
        }
        unsigned char *row=live.data+stride*used;
        bb_arena_store_v527(row,keys[i]);
        bb_arena_store_v527(row+8,cls);
        ++used;
        bb_arena_store_v527(h+16,live.va+stride*used);
    }
    if (!bb_class_sort_v556(live.data,capacity*stride,used)) return BB_SEC_STOP;
    return BB_SEC_OK;
}
#endif
