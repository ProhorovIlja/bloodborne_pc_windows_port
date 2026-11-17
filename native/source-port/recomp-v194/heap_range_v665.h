/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_HEAP_RANGE_V665_H
#define BB_HEAP_RANGE_V665_H
#include <stdint.h>
#include <string.h>

struct bb_heap_range_v665 { uintptr_t owner, begin, end; };
struct bb_heap_range_lock_v665 {
    void *ctx;
    int (*enter)(void *);
    void (*leave)(void *);
};
_Static_assert(sizeof(struct bb_heap_range_v665)==24,"64-bit heap range ABI");

/* Live V664 registry; storage and owner must outlive the call. All readers
 * must use the same exclusive lock or run before publication. Only disjoint
 * ranges with spare capacity are supported: reject duplicates, overlaps and
 * growth rather than entering the retail replacement/diagnostic paths. */
static inline int bb_heap_range_insert_v665(unsigned char *header,
        struct bb_heap_range_lock_v665 lock, uintptr_t owner, uintptr_t begin, uintptr_t size) {
    if (!header || !owner || !size || size>UINTPTR_MAX-begin ||
        !lock.enter || !lock.leave || !lock.enter(lock.ctx)) return 0;
    uintptr_t first, last, limit;
    memcpy(&first,header+8,8);
    memcpy(&last,header+16,8);
    memcpy(&limit,header+24,8);
    int ok=0;
    if (!first || first>last || last>limit || (last-first)%24 ||
        (limit-first)%24 || limit-last<24) goto done;
    struct bb_heap_range_v665 row={owner,begin,begin+size}, old;
    uintptr_t pos=last;
    for (uintptr_t p=first;p<last;p+=24) {
        memcpy(&old,(const void *)p,24);
        if (old.owner==owner || (old.begin<row.end && row.begin<old.end)) goto done;
        if (pos==last && row.begin<old.begin) pos=p;
    }
    memmove((void *)(pos+24),(const void *)pos,last-pos);
    memcpy((void *)pos,&row,24);
    last+=24;
    memcpy(header+16,&last,8);
    ok=1;
done:
    lock.leave(lock.ctx);
    return ok;
}
#endif
