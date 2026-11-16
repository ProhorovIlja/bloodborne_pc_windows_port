/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_RESERVE_V541_H
#define BB_REGISTRY_RESERVE_V541_H
#include "arena_seed_v527.h"
#include <string.h>

struct bb_vector_block_v541 { unsigned char *data; size_t size; uint64_t va; };
enum bb_vector_v541 { BB_VEC_INVALID, BB_VEC_UNCHANGED, BB_VEC_ALLOC, BB_VEC_RELEASE, BB_VEC_READY };
static inline uint64_t bb_vector_word_v541(const unsigned char *p) {
    uint64_t v=0;
    for (unsigned i=0;i<8;++i) v|=(uint64_t)p[i]<<(8*i);
    return v;
}
/* Startup reserve only, not registry insertion. Callback owns allocator
 * locking and backing storage; on failure after allocation, stop the session.
 * Header and backing buffers must be distinct in the host address space. */
static inline enum bb_vector_v541 bb_vector_reserve_v541(unsigned char *header,
        size_t n, uint64_t header_va, const struct bb_vector_block_v541 *old,
        void *ctx, int (*allocate)(void *,uint64_t,size_t,struct bb_vector_block_v541 *),
        int (*release)(void *,uint64_t,uint64_t)) {
    enum { stride=24, capacity=32, bytes=stride*capacity };
    if (!header || n<40 || !header_va || header_va>UINT64_MAX-40 || !allocate || !release)
        return BB_VEC_INVALID;
    const uint64_t begin=bb_vector_word_v541(header+8), end=bb_vector_word_v541(header+16),
        limit=bb_vector_word_v541(header+24), owner=bb_vector_word_v541(header+32);
    if (!owner || begin>end || end>limit || (begin&7) || (end-begin)%stride ||
        (limit-begin)%stride || (!begin && limit) ||
        (begin && (!old || old->va!=begin || !old->data || limit-begin>old->size ||
        (begin<header_va+40 && header_va<limit)))) return BB_VEC_INVALID;
    if (limit-begin>=bytes) return BB_VEC_UNCHANGED;
    struct bb_vector_block_v541 b={0};
    if (!allocate(ctx,owner,bytes,&b) || !b.data || b.size<bytes || !b.va ||
        (b.va&7) || b.va>UINT64_MAX-bytes ||
        (b.va<header_va+40 && header_va<b.va+bytes) ||
        (begin && (b.va==begin || (b.va<limit && begin<b.va+bytes)))) return BB_VEC_ALLOC;
    const size_t used=(size_t)(end-begin);
    if (used) memmove(b.data,old->data,used);
    if (begin && !release(ctx,owner,begin)) return BB_VEC_RELEASE;
    bb_arena_store_v527(header+24,b.va+bytes);
    bb_arena_store_v527(header+16,b.va+used);
    bb_arena_store_v527(header+8,b.va);
    return BB_VEC_READY;
}
#endif
