/* SPDX-License-Identifier: GPL-2.0-or-later
 * Coalescing adapted from Paleblood, game/engine/regular_heap_free.cpp.
 */
#ifndef BB_REGULAR_HEAP_FREE_V662_H
#define BB_REGULAR_HEAP_FREE_V662_H
#include "regular_heap_allocate_v661.h"

static inline void bb_heap_unlink_v662(uintptr_t h, uintptr_t b, uintptr_t end) {
    if (end-b==16) return;
    const uintptr_t prev=bb_load_v661(b+16), next=bb_load_v661(b+24);
    bb_store_v661(prev+24,next);
    bb_store_v661(next+16,prev);
    if (prev==next)
        bb_store_v661(h,bb_load_v661(h)&~(UINT64_C(1)<<bb_bucket_v661(end-b)));
}

/* Exclusive access to a live V660 heap. Payload must be a live allocation
 * from that heap or NULL; cheap guards are not an arbitrary pointer validator. */
static inline int bb_heap_free_v662(unsigned char *heap, void *payload) {
    if (!payload) return 1;
    if (!heap) return 0;
    const uintptr_t h=(uintptr_t)heap, p=(uintptr_t)payload;
    const uintptr_t low=bb_load_v661(h+8), high=bb_load_v661(h+16);
    if (p<low || p>=high || (p&15)) return 0;
    const uintptr_t b=p-16, flags=bb_load_v661(b+8), next=flags&~(uintptr_t)3;
    const uintptr_t count=bb_load_v661(h+32);
    if (!(flags&1) || !count || next<=b || next>high-16 || (next&15)) return 0;
    uintptr_t start=b, end=next;
    bb_store_v661(h+24,bb_load_v661(h+24)+(next-b));
    bb_store_v661(h+32,count-1);
    if (!(flags&2)) {
        start=bb_load_v661(b);
        bb_heap_unlink_v662(h,start,b);
        bb_store_v661(b+8,flags-1);
    }
    const uintptr_t following=bb_load_v661(next+8);
    if (following&1) {
        bb_store_v661(start+8,next|2);
        bb_store_v661(next,start);
        bb_store_v661(next+8,following-2);
    } else {
        end=following-2;
        bb_store_v661(start+8,following);
        bb_store_v661(end,start);
        bb_heap_unlink_v662(h,next,end);
    }
    const unsigned k=bb_bucket_v661(end-start);
    const uintptr_t s=bb_sentinel_v661(h,k), first=bb_load_v661(s+24);
    bb_store_v661(s+24,start);
    bb_store_v661(start+16,s);
    bb_store_v661(start+24,first);
    bb_store_v661(first+16,start);
    if (first==s) bb_store_v661(h,bb_load_v661(h)|(UINT64_C(1)<<k));
    return 1;
}
#endif
