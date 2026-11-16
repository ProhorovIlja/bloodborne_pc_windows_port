/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_SINGLETON_V525_H
#define BB_SINGLETON_V525_H
#include "ctor_route_v524.h"

struct bb_singleton_v525 {
    size_t published, storage, lock_slot, unlock_slot;
    uint64_t lock_id, unlock_id;
};
enum bb_singleton_status_v525 { BB_SINGLETON_MISS, BB_SINGLETON_OK, BB_SINGLETON_UNLOCK_FAILED };
/* Serialized startup only. The existing published address is returned as an
 * opaque guest value. On the cold path, publish only after native init returns.
 * On a miss after locking, release the host lock, but never retry the startup. */
static inline enum bb_singleton_status_v525 bb_singleton_guarded_v530(
        unsigned char *rw, size_t n, const struct bb_ctor_route_v524 *p,
        const struct bb_singleton_v525 *s, bb_call_v521 guard,
        int (*sync)(void *, uint64_t, uint64_t, uint32_t),
        int (*init)(void *, uint64_t), void *ctx, uint64_t *out,
        const size_t *inner_guard) {
    if (!rw || !p || !s || !out || n<17 || n>UINT64_MAX-p->base ||
        s->published>n-8 || s->storage>=n ||
        (inner_guard && (*inner_guard>=n || *inner_guard==p->guard ||
         *inner_guard==p->done || (*inner_guard>=s->published && *inner_guard-s->published<8)))) return BB_SINGLETON_MISS;
    const uint64_t old=bb_read64_v524(rw+s->published);
    if (old) { *out=old; return BB_SINGLETON_OK; }
    if (!sync || !init || s->lock_slot>n-8 || s->unlock_slot>n-8 ||
        !s->lock_id || !s->unlock_id ||
        bb_read64_v524(rw+s->lock_slot)!=s->lock_id ||
        bb_read64_v524(rw+s->unlock_slot)!=s->unlock_id ||
        !bb_guard_prefix_v521(rw,n,p->base,p->guard,p->done,p->storage,p->vtable,guard,ctx))
        return BB_SINGLETON_MISS;
    const size_t obj=p->storage+(size_t)((UINT64_C(0)-(p->base+p->storage))&7);
    const uint64_t aligned=(p->base+s->storage), pad=(UINT64_C(0)-aligned)&7;
    if (pad>=n-s->storage || bb_read64_v524(rw+obj)!=p->vtable || !rw[obj+16] ||
        bb_read64_v524(rw+s->lock_slot)!=s->lock_id ||
        bb_read64_v524(rw+s->unlock_slot)!=s->unlock_id ||
        !sync(ctx,s->lock_id,p->base+obj,UINT32_MAX)) return BB_SINGLETON_MISS;
    uint64_t value=bb_read64_v524(rw+s->published);
    int ok=value!=0;
    if (!ok) {
        value=aligned+pad;
        uint32_t acquired=0;
        ok=1;
        /* The allocation object's guard is distinct from the mutex object's
         * guard. The original releases it before the void initializer. */
        if (inner_guard && !rw[*inner_guard]) {
            const uint64_t address=p->base+*inner_guard;
            ok=guard(ctx,BB_ACQUIRE_V521,address,&acquired);
            if (ok && acquired) ok=guard(ctx,BB_RELEASE_V521,address,&acquired);
        }
        if (ok) ok=init(ctx,value);
        if (ok) for (unsigned i=0;i<8;++i) rw[s->published+i]=(unsigned char)(value>>(i*8));
    }
    if (!sync(ctx,s->unlock_id,p->base+obj,0)) return BB_SINGLETON_UNLOCK_FAILED;
    if (!ok) return BB_SINGLETON_MISS;
    *out=value;
    return BB_SINGLETON_OK;
}
static inline enum bb_singleton_status_v525 bb_singleton_get_v525(
        unsigned char *rw, size_t n, const struct bb_ctor_route_v524 *p,
        const struct bb_singleton_v525 *s, bb_call_v521 guard,
        int (*sync)(void *, uint64_t, uint64_t, uint32_t),
        int (*init)(void *, uint64_t), void *ctx, uint64_t *out) {
    return bb_singleton_guarded_v530(rw,n,p,s,guard,sync,init,ctx,out,NULL);
}
#endif
