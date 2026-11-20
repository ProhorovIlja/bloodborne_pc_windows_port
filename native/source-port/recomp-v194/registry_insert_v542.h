/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_INSERT_V542_H
#define BB_REGISTRY_INSERT_V542_H
#include "registry_reserve_v541.h"

enum bb_insert_v542 { BB_INSERT_INVALID, BB_INSERT_DUPLICATE, BB_INSERT_FULL,
    BB_INSERT_STOP, BB_INSERT_OK };
/* In-capacity path. Caller owns the registry lock and backing lifetime.
 * A diagnostic that does not return stops before any write. */
static inline enum bb_insert_v542 bb_registry_insert_route_v543(unsigned char *h,
        size_t size,const struct bb_vector_block_v541 *b,uint64_t key,
        uint64_t first,uint64_t extent,int (*warn)(void *),void *ctx,
        size_t *full_position) {
    if (!h || size<40 || !warn || !key || !extent ||
        extent>UINT64_MAX-first) return BB_INSERT_INVALID;
    const uint64_t lo=bb_vector_word_v541(h+8), hi=bb_vector_word_v541(h+16),
        cap=bb_vector_word_v541(h+24), last=first+extent;
    if (!lo) {
        if (hi || cap) return BB_INSERT_INVALID;
        if (full_position) *full_position=0;
        return BB_INSERT_FULL;
    }
    if (!b || !b->data || (lo&7) || lo!=b->va || lo>hi || hi>cap || cap-lo>b->size ||
        (hi-lo)%24 || (cap-lo)%24) return BB_INSERT_INVALID;
    size_t pos=(size_t)(hi-lo);
    int candidate=0;
    while (pos) {
        const unsigned char *r=b->data+pos-24;
        const uint64_t end=bb_vector_word_v541(r+16);
        if (end<=first) { candidate=1; break; }
        if (bb_vector_word_v541(r+8)<=first) {
            if (end<last && !warn(ctx)) return BB_INSERT_STOP;
            candidate=1;
            break;
        }
        pos-=24;
    }
    if (candidate && bb_vector_word_v541(b->data+pos-24)==key) return BB_INSERT_DUPLICATE;
    if (hi==cap) {
        if (full_position) *full_position=pos;
        return BB_INSERT_FULL;
    }
    memmove(b->data+pos+24,b->data+pos,(size_t)(hi-lo)-pos);
    bb_arena_store_v527(b->data+pos,key);
    bb_arena_store_v527(b->data+pos+8,first);
    bb_arena_store_v527(b->data+pos+16,last);
    bb_arena_store_v527(h+16,hi+24);
    return BB_INSERT_OK;
}
static inline enum bb_insert_v542 bb_registry_insert_v542(unsigned char *h,
        size_t size,const struct bb_vector_block_v541 *b,uint64_t key,
        uint64_t first,uint64_t extent,int (*warn)(void *),void *ctx) {
    return bb_registry_insert_route_v543(h,size,b,key,first,extent,warn,ctx,NULL);
}
#endif
