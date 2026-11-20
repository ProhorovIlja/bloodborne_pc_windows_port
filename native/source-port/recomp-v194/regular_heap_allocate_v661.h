/* SPDX-License-Identifier: GPL-2.0-or-later
 * Allocation algorithm adapted from Yharnam-Hunters/Paleblood,
 * game/engine/regular_heap_allocate.cpp and regular_heap.h.
 */
#ifndef BB_REGULAR_HEAP_ALLOCATE_V661_H
#define BB_REGULAR_HEAP_ALLOCATE_V661_H
#include "regular_heap_seed_v660.h"

static inline uintptr_t bb_load_v661(uintptr_t p) {
    uintptr_t v;
    memcpy(&v, (const void *)p, sizeof v);
    return v;
}
static inline void bb_store_v661(uintptr_t p, uintptr_t v) {
    bb_heap_word_v660((unsigned char *)p, v);
}
static inline unsigned bb_bucket_v661(uintptr_t n) {
    unsigned k=0;
    while (n>1) { n>>=1; ++k; }
    return k;
}
static inline uintptr_t bb_sentinel_v661(uintptr_t h, unsigned k) {
    return h+0x18+16*k;
}

/* Live V660 heap with valid internal links and exclusive access. Supports
 * the original plain allocation path only (alignment <= 16); no fallback. */
static inline void *bb_heap_allocate_v661(unsigned char *heap, uintptr_t request, uintptr_t alignment) {
    if (!heap || alignment>16 || (alignment & (alignment-1)) || request>UINTPTR_MAX-23)
        return NULL;
    const uintptr_t h=(uintptr_t)heap, available=bb_load_v661(h+24);
    if (available<request) return NULL;
    const uintptr_t size=request<=24 ? 32 : (request+23)&~(uintptr_t)15;
    uintptr_t mask=bb_load_v661(h);
    unsigned k=bb_bucket_v661(size);
    const uint64_t larger=(uint64_t)mask & (UINT64_C(0xfffffffffffffffe)<<k);
    uintptr_t block;
    if (larger) {
        do { ++k; } while (!(larger & (UINT64_C(1)<<k)));
        block=bb_load_v661(bb_sentinel_v661(h,k)+24);
    } else {
        if (!((mask>>k)&1)) return NULL;
        const uintptr_t s=bb_sentinel_v661(h,k);
        for (block=bb_load_v661(s+24); block!=s; block=bb_load_v661(block+24))
            if ((bb_load_v661(block+8)&~(uintptr_t)3)-block>=size) break;
        if (block==s) return NULL;
    }
    const uintptr_t word=bb_load_v661(block+8), next=word-2;
    const uintptr_t prev_link=bb_load_v661(block+16), next_link=bb_load_v661(block+24);
    bb_store_v661(prev_link+24,next_link);
    bb_store_v661(next_link+16,prev_link);
    if (prev_link==next_link) mask&=~(UINT64_C(1)<<k);
    bb_store_v661(h+24,available-size);
    bb_store_v661(h+32,bb_load_v661(h+32)+1);
    const uintptr_t rest=block+size;
    if (rest==next) {
        bb_store_v661(next+8,bb_load_v661(next+8)+2);
        bb_store_v661(block+8,word+1);
    } else {
        bb_store_v661(block+8,rest|3);
        bb_store_v661(rest+8,word);
        bb_store_v661(next,rest);
        if (next-rest!=16) {
            k=bb_bucket_v661(next-rest);
            const uintptr_t s=bb_sentinel_v661(h,k), first=bb_load_v661(s+24);
            bb_store_v661(s+24,rest);
            bb_store_v661(rest+16,s);
            bb_store_v661(rest+24,first);
            bb_store_v661(first+16,rest);
            mask|=UINT64_C(1)<<k;
        }
    }
    bb_store_v661(h,mask);
    return (void *)(block+16);
}
#endif
