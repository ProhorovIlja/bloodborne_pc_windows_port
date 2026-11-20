/* SPDX-License-Identifier: GPL-2.0-or-later
 * Heap layout and initialization adapted from Yharnam-Hunters/Paleblood,
 * game/engine/regular_heap_initialize.cpp and regular_heap.h.
 */
#ifndef BB_REGULAR_HEAP_SEED_V660_H
#define BB_REGULAR_HEAP_SEED_V660_H
#include "dependency_seed_v659.h"

enum { BB_HEAP_HEADER_V660 = 0x440, BB_HEAP_BACKING_V660 = 0x100000 };
static inline void bb_heap_word_v660(unsigned char *p, uintptr_t value) {
    memcpy(p,&value,8);
}
/* Exclusive, live, disjoint buffers. A short usable range clears the heap;
 * impossible pointer arithmetic and overlapping spans are rejected first. */
static inline int bb_heap_seed_v660(unsigned char *heap, size_t heap_size,
        unsigned char *memory, size_t size) {
    const uintptr_t h=(uintptr_t)heap, a=(uintptr_t)memory;
    if (!h || !a || sizeof(uintptr_t)!=8 || (h&7) || heap_size<BB_HEAP_HEADER_V660 ||
        h>UINTPTR_MAX-BB_HEAP_HEADER_V660 || a>UINTPTR_MAX-23 || size>UINTPTR_MAX-a ||
        (h<a+size && a<h+BB_HEAP_HEADER_V660)) return 0;
    const uintptr_t low=(a+23)&~(uintptr_t)15;
    const uintptr_t high=size>=8 ? (a+size-8)&~(uintptr_t)15 : 0;
    if (high<low || high-low<64) {
        memset(heap,0,BB_HEAP_HEADER_V660);
        return 0;
    }
    const uintptr_t first=low-16, end=high-16, available=end-first;
    unsigned bucket=0;
    for (uintptr_t n=available;n>1;n>>=1) ++bucket;
    bb_heap_word_v660(heap,UINT64_C(1)<<bucket);
    bb_heap_word_v660(heap+8,low);
    bb_heap_word_v660(heap+16,high);
    bb_heap_word_v660(heap+24,available);
    bb_heap_word_v660(heap+32,0);
    for (size_t i=0;i<64;++i) {
        const size_t off=0x28+16*i;
        const uintptr_t sentinel=h+off-16;
        const uintptr_t link=i==bucket ? first : sentinel;
        bb_heap_word_v660(heap+off,link);
        bb_heap_word_v660(heap+off+8,link);
    }
    bb_heap_word_v660(heap+0x428,first);
    bb_heap_word_v660(heap+0x430,end);
    bb_heap_word_v660(heap+0x438,available);
    unsigned char *f=memory+(low-8-a), *e=memory+(end-a);
    const uintptr_t sentinel=h+0x18+16*bucket;
    bb_heap_word_v660(f,end|2);
    bb_heap_word_v660(f+8,sentinel);
    bb_heap_word_v660(f+16,sentinel);
    bb_heap_word_v660(e,first);
    bb_heap_word_v660(e+8,first|1);
    return 1;
}
#endif
