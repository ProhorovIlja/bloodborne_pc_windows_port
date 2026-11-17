/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_BATCH_V651_H
#define BB_REGISTRY_BATCH_V651_H
#include "registry_rows_v650.h"

struct bb_pending_v651 { uint64_t target, object; };
_Static_assert(sizeof(struct bb_pending_v651)==16, "pending entry layout");
struct bb_registry_v651 {
    struct bb_registry_row_v650 *rows;
    struct bb_pending_v651 *pending;
    size_t count, capacity, used, reserved;
};
struct bb_registry_allocator_v651 {
    void *ctx;
    void *(*allocate)(void *, size_t, size_t);
    void (*release)(void *, void *);
};

/* Final capacity on a successful append. Batch preflight may coalesce
 * allocations. Deliberately does not reproduce the retail OOM diagnostics. */
static inline size_t bb_registry_capacity_v651(size_t n, size_t cap,
                                               size_t add, size_t width) {
    if (!width || !add) return 0;
    const size_t max=SIZE_MAX/width;
    if (n>cap || cap>max || add>max-n) return 0;
    if (!n && cap<512) {
        if (max<512) return 0;
        cap=512;
    }
    while (cap<n+add) {
        const size_t half=cap/2;
        cap=(half && half<=max-cap) ? cap+half : cap+1;
    }
    return cap;
}

/* Exclusive ownership of both arrays and immutable allocator callbacks.
 * Allocate must return fresh, aligned storage; release cannot fail/reenter.
 * All four resolved targets are staged, not invoked here. */
static inline int bb_registry_register_v651(struct bb_registry_v651 *v,
        const struct bb_registry_allocator_v651 *a, struct bb_registry_row_v650 row,
        const uint64_t targets[static 4]) {
    if (!v || !a || !a->allocate || !a->release || !row.object || !row.name ||
        !!v->rows != !!v->capacity || !!v->pending != !!v->reserved) return 0;
    struct bb_pending_v651 batch[4];
    for (size_t i=0;i<4;++i) batch[i]=(struct bb_pending_v651){targets[i],row.object};
    const size_t rc=bb_registry_capacity_v651(v->count,v->capacity,1,sizeof *v->rows);
    const size_t pc=bb_registry_capacity_v651(v->used,v->reserved,4,sizeof *v->pending);
    if (!rc || !pc) return 0;
    struct bb_registry_row_v650 *rows=v->rows;
    struct bb_pending_v651 *pending=v->pending;
    if (rc!=v->capacity) {
        rows=a->allocate(a->ctx,rc*sizeof *rows,8);
        if (!rows) return 0;
        if (v->count) memcpy(rows,v->rows,v->count*sizeof *rows);
    }
    if (pc!=v->reserved) {
        pending=a->allocate(a->ctx,pc*sizeof *pending,8);
        if (!pending) {
            if (rows!=v->rows) a->release(a->ctx,rows);
            return 0;
        }
        if (v->used) memcpy(pending,v->pending,v->used*sizeof *pending);
    }
    size_t n=v->count;
    if (!bb_registry_insert_v650(rows,&n,rc,row)) {
        if (rows!=v->rows) a->release(a->ctx,rows);
        if (pending!=v->pending) a->release(a->ctx,pending);
        return 0;
    }
    memcpy(pending+v->used,batch,sizeof batch);
    if (rows!=v->rows && v->rows) a->release(a->ctx,v->rows);
    if (pending!=v->pending && v->pending) a->release(a->ctx,v->pending);
    *v=(struct bb_registry_v651){rows,pending,n,rc,v->used+4,pc};
    return 1;
}
#endif
