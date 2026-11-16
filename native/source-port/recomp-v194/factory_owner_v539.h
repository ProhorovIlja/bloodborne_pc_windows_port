/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_FACTORY_OWNER_V539_H
#define BB_FACTORY_OWNER_V539_H
#include "factory_child_v539.h"
#include "startup_rwlock_host_v539.h"

/* Private, serialized candidate object. Does not publish the owner. No
 * default ABI for a different vtable, owner, or non-default attributes. */
struct bb_owner_v539 {
    ShytStartupRwlockV414 lock;
    unsigned char *body;
    uint64_t va;
};
static inline int bb_owner_init_lock_v539(void *ctx,uint64_t slot,uint32_t *rc) {
    struct bb_owner_v539 *o=ctx;
    if (slot!=o->va+0x478 || o->lock.live) return 0;
    *rc=UINT32_C(0x80020023);
    if (shyt_rw_init_v414(&o->lock)) {
        bb_factory_put_v538(o->body+0x478,SHYT_RW_TOKEN_V414,8);
        *rc=0;
    }
    return 1;
}
static inline int bb_owner_stop_v539(void *ctx,unsigned line) {
    (void)ctx; (void)line; return 0;
}
static inline int bb_owner_child_v539(void *ctx,uint64_t va) {
    struct bb_owner_v539 *o=ctx;
    if (va!=o->va+0x470) return 0;
    return bb_child_init_v539(o->body+0x470,17,va,o,
        bb_owner_init_lock_v539,bb_owner_stop_v539).status==BB_CHILD_READY;
}
static inline int bb_owner_seed_v539(struct bb_owner_v539 *o,
        unsigned char *p,size_t n,uint64_t va,uint64_t t0,uint64_t t1,uint64_t t2) {
    if (!o || o->body || o->lock.live || !p || n<0x48c || !va ||
        (va&7) || va>UINT64_MAX-0x48c || !t0 || !t1 || !t2) return 0;
    o->body=p; o->va=va;
    return bb_factory_seed_v538(p,n,va,t0,t1,t2,bb_owner_child_v539,o);
}
#endif
