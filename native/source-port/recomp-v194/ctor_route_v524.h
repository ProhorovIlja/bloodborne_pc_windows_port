/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CTOR_ROUTE_V524_H
#define BB_CTOR_ROUTE_V524_H
#include "guard_prefix_v521.h"

/* Constructor shape: publish a callback, initialize the shared object, then
 * check the virtual predicate. Guest addresses never become host pointers. */
struct bb_ctor_route_v524 {
    uint64_t base, callback, vtable, predicate;
    size_t publish, guard, done, storage, predicate_slot;
};
static inline uint64_t bb_read64_v524(const unsigned char *p) {
    uint64_t v=0;
    for (unsigned i=0;i<8;++i) v|=(uint64_t)p[i]<<(i*8);
    return v;
}
static inline int bb_ctor_route_v524(unsigned char *rw,size_t n,
        const struct bb_ctor_route_v524 *p,bb_call_v521 hook,void *ctx) {
    if (!rw || !p || !hook || n<17 || p->publish>n-8 || p->storage>n-17 ||
        p->guard>=n || p->done>=n || p->guard==p->done || n>UINT64_MAX-p->base ||
        !p->callback || !p->vtable || !p->predicate || p->predicate_slot>n-8 ||
        bb_read64_v524(rw+p->predicate_slot)!=p->predicate) return 0;
    const size_t pad=(size_t)((UINT64_C(0)-(p->base+p->storage))&7);
    if (pad>n-17-p->storage) return 0;
    const size_t obj=p->storage+pad, pub=p->publish, slot=p->predicate_slot;
    if ((pub<obj+17 && obj<pub+8) || (slot<obj+17 && obj<slot+8) ||
        (pub<slot+8 && slot<pub+8) ||
        (p->guard>=obj && p->guard<obj+17) || (p->done>=obj && p->done<obj+17) ||
        (p->guard>=pub && p->guard<pub+8) || (p->done>=pub && p->done<pub+8) ||
        (p->guard>=slot && p->guard<slot+8) || (p->done>=slot && p->done<slot+8)) return 0;
    for (unsigned i=0;i<8;++i) rw[pub+i]=(unsigned char)(p->callback>>(i*8));
    if (!bb_guard_prefix_v521(rw,n,p->base,p->guard,p->done,p->storage,p->vtable,hook,ctx)) return 0;
    /* A different virtual target or a false predicate would enter an
     * unimplemented path. Stop; the published callback may already exist. */
    return bb_read64_v524(rw+obj)==p->vtable &&
        bb_read64_v524(rw+slot)==p->predicate && rw[obj+16]!=0;
}
#endif
