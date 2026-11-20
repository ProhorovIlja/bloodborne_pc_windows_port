/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_STARTUP_V548_H
#define BB_REGISTRY_STARTUP_V548_H
#include "registry_grow_v543.h"
#include "startup_rwlock_host_v539.h"
#include "startup_transaction_v547.h"

enum bb_alloc_v548 { BB_ALLOC_ERROR, BB_ALLOC_NO_SPACE, BB_ALLOC_OK };
struct bb_registry_driver_v548 {
    void *ctx;
    enum bb_alloc_v548 (*allocate)(void *,uint64_t,size_t,struct bb_vector_block_v541 *);
    int (*release)(void *,uint64_t,uint64_t);
};
struct bb_registry_tls_v548 {
    unsigned char *data;
    size_t size,tp;
    uint64_t base,file;
    int64_t mark,active,jump;
};
struct bb_registry_result_v548 {
    enum bb_insert_v542 insert;
    struct bb_transaction_v547 action;
    int unlocked;
};
struct bb_registry_alloc_v548 { const struct bb_registry_driver_v548 *driver; int oom; };
static inline int bb_registry_allocate_v548(void *ctx,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    struct bb_registry_alloc_v548 *s=ctx;
    const enum bb_alloc_v548 r=s->driver->allocate(s->driver->ctx,owner,n,out);
    s->oom=(r==BB_ALLOC_NO_SPACE);
    return r==BB_ALLOC_OK;
}
static inline int bb_registry_release_v548(void *ctx,uint64_t owner,uint64_t va) {
    const struct bb_registry_alloc_v548 *s=ctx;
    return s->driver->release(s->driver->ctx,owner,va);
}
/* Bounded startup route, not a general PS4 unwind. Allocator callbacks must
 * release their own lock before returning. Unwind the registry writer before
 * exposing a terminal action; never treat an allocator contract error as OOM. */
static inline struct bb_registry_result_v548 bb_registry_startup_v548(
        ShytStartupRwlockV414 *writer,const struct bb_registry_tls_v548 *tls,
        unsigned char *h,size_t size,uint64_t hva,const struct bb_vector_block_v541 *old,
        uint64_t key,uint64_t first,uint64_t extent,int (*warn)(void *),void *warn_ctx,
        const struct bb_registry_driver_v548 *driver) {
    struct bb_registry_result_v548 out={BB_INSERT_INVALID,{BB_TX_INVALID,0,0},0};
    if (!writer || !writer->live || writer->held || !tls || !driver || !driver->allocate ||
        !driver->release || !bb_tls_mark_v547(tls->data,tls->size,tls->tp,tls->mark,tls->file) ||
        !shyt_rw_write_v414(writer)) return out;
    struct bb_registry_alloc_v548 s={driver,0};
    const struct bb_growth_v543 growth={&s,bb_registry_allocate_v548,bb_registry_release_v548};
    out.insert=bb_registry_grow_v543(h,size,hva,old,key,first,extent,warn,warn_ctx,&growth);
    out.unlocked=shyt_rw_unlock_v414(writer);
    if (!out.unlocked) out.insert=BB_INSERT_STOP;
    else if (s.oom) out.action=bb_tls_oom_v547(tls->data,tls->size,tls->base,tls->tp,tls->active,tls->jump);
    return out;
}
#endif
