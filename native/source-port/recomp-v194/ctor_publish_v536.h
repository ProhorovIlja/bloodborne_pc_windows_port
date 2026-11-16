/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CTOR_PUBLISH_V536_H
#define BB_CTOR_PUBLISH_V536_H
#include <stddef.h>
#include "ctor_route_v524.h"

enum bb_publish_status_v536 { BB_PUBLISH_MISS, BB_PUBLISH_OK, BB_PUBLISH_DIAG };
struct bb_publish_layout_v536 {
    uint64_t base, initial_table, final_table, source_bias;
    size_t storage, cache, published;
};
static inline void bb_publish_store_v536(unsigned char *dst, uint64_t v) {
    for (unsigned i=0;i<8;++i) dst[i]=(unsigned char)(v>>(8*i));
}
/* Called after the constructor's guard phase. Hooks resolve guest values;
 * a failed hook may leave partial writes. Stop without retrying. */
static inline enum bb_publish_status_v536 bb_ctor_publish_v536(
        unsigned char *rw, size_t n, const struct bb_publish_layout_v536 *p,
        void *ctx, int (*source)(void *,uint64_t *),
        int (*flags)(void *,uint64_t,uint32_t *), int (*diagnostic)(void *),
        uint64_t *out) {
    if (!rw || !p || !out || n<80 || n>UINT64_MAX-p->base ||
        p->published>n-8 || p->cache>n-8 || p->storage>n-80 ||
        !p->initial_table || !p->final_table || !source || !flags || !diagnostic)
        return BB_PUBLISH_MISS;
    const size_t pad=(size_t)((UINT64_C(0)-(p->base+p->storage))&7);
    if (pad>n-80-p->storage) return BB_PUBLISH_MISS;
    const size_t a=p->storage+pad, c=p->cache, d=p->published;
    if ((a<d+8 && d<a+80) || (a<c+8 && c<a+80) ||
        (c<d+8 && d<c+8) || !((uint64_t)a+p->base)) return BB_PUBLISH_MISS;
    const uint64_t old=bb_read64_v524(rw+d);
    if (old) { *out=old; return BB_PUBLISH_OK; }
    unsigned char *obj=rw+a;
    bb_publish_store_v536(obj,p->initial_table);
    bb_publish_store_v536(obj+8,0);
    bb_publish_store_v536(obj+16,0);
    uint64_t owner=bb_read64_v524(rw+c);
    if (!owner) {
        if (!source(ctx,&owner) || !owner || owner>UINT64_MAX-p->source_bias)
            return BB_PUBLISH_MISS;
        owner+=p->source_bias;
        bb_publish_store_v536(rw+c,owner);
    }
    uint32_t bits;
    if (!flags(ctx,owner,&bits)) return BB_PUBLISH_MISS;
    if (!(bits&32) && !diagnostic(ctx)) return BB_PUBLISH_DIAG;
    for (size_t i=32;i<=72;i+=8) bb_publish_store_v536(obj+i,i==56?owner:0);
    bb_publish_store_v536(obj,p->final_table);
    bb_publish_store_v536(rw+d,p->base+a);
    *out=p->base+a;
    return BB_PUBLISH_OK;
}
#endif
