/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_MEMBER_HANDLERS_V610_H
#define BB_MEMBER_HANDLERS_V610_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    uintptr_t *begin,*end,*limit;
    void *allocator;
} BbHandlerVector610;
typedef struct {
    uintptr_t *(*allocate)(void *,size_t,size_t);
    void (*release)(void *,uintptr_t *);
} BbHandlerOps610;
_Static_assert(sizeof(uintptr_t)==8 && offsetof(BbHandlerVector610,allocator)==24,
               "64-bit handler ABI required");

/* Serialized access; old storage is live and allocate returns a distinct
 * aligned allocation. Slots are resolved host targets, not guest addresses.
 * Unlike retail's diagnostic branch, allocation failure returns to caller. */
static inline int bb_handler_append_v610(BbHandlerVector610 *v,uintptr_t handler,
                                         const BbHandlerOps610 *op) {
    if (!v || !op || !op->allocate || !op->release || !v->allocator || !handler) return -1;
    const uintptr_t b=(uintptr_t)v->begin,e=(uintptr_t)v->end,l=(uintptr_t)v->limit;
    if ((b|e|l)&7 || b>e || e>l || (!b && l)) return -1;
    const size_t used=(e-b)/8,cap=(l-b)/8;
    if (used==cap) {
        const size_t max=SIZE_MAX/8;
        if (cap>=max) return -1;
        size_t next=cap/2<=max-cap?cap+cap/2:cap+1;
        if (next<=cap) next=cap+1;
        if (!cap) next=4;
        uintptr_t *p=op->allocate(v->allocator,next*8,8);
        if (!p) return 0;
        if (used) memcpy(p,v->begin,used*8);
        if (v->begin) op->release(v->allocator,v->begin);
        v->begin=p;
        v->end=p+used;
        v->limit=p+next;
    }
    *v->end++=handler;
    return 1;
}
#endif
