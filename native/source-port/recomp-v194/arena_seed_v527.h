/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_V527_H
#define BB_ARENA_V527_H
#include <stddef.h>
#include <stdint.h>

/* Startup arena metadata only: never dereference guest addresses. The caller
 * supplies separate object/arena buffers, their guest addresses and layout.
 * The layout spans the bitmap, bin heads, then the three trailer words. */
static inline void bb_arena_store_v527(unsigned char *p, uint64_t value) {
    for (unsigned i=0;i<8;++i) p[i]=(unsigned char)(value>>(8*i));
}
static inline int bb_arena_seed_v527(unsigned char *obj, size_t obj_size,
        size_t bitmap, uint64_t obj_va, unsigned char *arena, size_t size,
        uint64_t arena_va) {
    enum { bins=64, header=40, trailer=header+bins*16, used=trailer+24 };
    if (!obj || !arena || obj_size<used || bitmap>obj_size-used ||
        obj_size>UINT64_MAX-obj_va || !arena_va || size<128 ||
        size>UINT64_MAX-arena_va || UINT64_MAX-arena_va<23 ||
        ((obj_va+bitmap)&7)) return 0;
    if (obj_va<arena_va+size && arena_va<obj_va+obj_size) return 0;
    const uint64_t first=(arena_va+23)&~UINT64_C(15);
    const uint64_t end=(arena_va+size-8)&~UINT64_C(15);
    if (end<first || end-first<64 || first-arena_va<16) return 0;
    const uint64_t span=end-first, left=first-16, right=end-16;
    unsigned bin=0;
    for (uint64_t v=span;v>1;v>>=1) ++bin;
    unsigned char *m=obj+bitmap;
    const uint64_t va=obj_va+bitmap;
    bb_arena_store_v527(m,UINT64_C(1)<<bin);
    bb_arena_store_v527(m+8,first);
    bb_arena_store_v527(m+16,end);
    bb_arena_store_v527(m+24,span);
    bb_arena_store_v527(m+32,0);
    for (unsigned i=0;i<bins;++i) {
        const uint64_t head=va+24+16*i;
        bb_arena_store_v527(m+header+16*i,i==bin?left:head);
        bb_arena_store_v527(m+header+16*i+8,i==bin?left:head);
    }
    bb_arena_store_v527(m+trailer,left);
    bb_arena_store_v527(m+trailer+8,right);
    bb_arena_store_v527(m+trailer+16,span);
    unsigned char *a=arena+(size_t)(left-arena_va), *b=arena+(size_t)(right-arena_va);
    const uint64_t head=va+24+16*bin;
    bb_arena_store_v527(a+8,right|2);
    bb_arena_store_v527(a+16,head);
    bb_arena_store_v527(a+24,head);
    bb_arena_store_v527(b,left);
    bb_arena_store_v527(b+8,left|1);
    return 1;
}
#endif
