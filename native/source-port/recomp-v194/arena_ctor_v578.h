/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_CTOR_V578_H
#define BB_ARENA_CTOR_V578_H
#include "arena_seed_v577.h"
#include "native_direct_memory_v411.h"

enum bb_arena_result_v578 { BB_ARENA_INVALID, BB_ARENA_OK, BB_ARENA_MUTEX,
    BB_ARENA_ALLOC, BB_ARENA_MAP, BB_ARENA_LAYOUT, BB_ARENA_CLEANUP };
struct bb_arena_binding_v578 {
    ShytDmPool *pool;
    const ShytDmBackend *backend;
    uint64_t arena_table, mutex_table;
    int (*mutex_init)(void *, unsigned char *);
    void *context;
};
/* Single startup controller. Stable fresh object, immutable native bindings.
 * Failures are terminal for this object; the owner must clean up any initialized
 * mutex. A cleanup failure leaves the reservation in the pool for the owner.
 * This intentionally stops instead of continuing after a retail diagnostic. */
static inline enum bb_arena_result_v578 bb_arena_ctor_v578(
    unsigned char *obj,size_t n,const struct bb_arena_binding_v578 *b) {
    if (!obj || n<BB_ARENA_OBJECT_V577 || sizeof(uintptr_t)!=8 || ((uintptr_t)obj&7) ||
        !b || !b->pool || !b->pool->limit || b->pool->limit>INT64_MAX ||
        !b->backend || !b->backend->map || !b->backend->unmap || !b->arena_table ||
        !b->mutex_table || !b->mutex_init) return BB_ARENA_INVALID;
    bb_arena_qword_v577(obj,b->arena_table);
    bb_arena_qword_v577(obj+8,(uintptr_t)obj);
    bb_arena_qword_v577(obj+0x10,b->mutex_table);
    obj[0x20]=0;
    memset(obj+0x28,0,0x460);
    if (b->mutex_init(b->context,obj+0x18)) return BB_ARENA_MUTEX;
    obj[0x20]=1;
    const uint64_t len=BB_ARENA_SIZE_V577, align=BB_ARENA_ALIGN_V577;
    uint64_t off=0;
    if (shyt_dm_allocate(b->pool,0,(int64_t)b->pool->limit,len,align,0,&off)!=SHYT_DM_OK)
        return BB_ARENA_ALLOC;
    void *mapped=NULL;
    enum bb_arena_result_v578 failure=BB_ARENA_MAP;
    if (shyt_dm_map(b->pool,b->backend,off,len,align,3,0,&mapped)==SHYT_DM_OK) {
        if (bb_arena_seed_v577(obj,n,mapped,(size_t)len,off)) return BB_ARENA_OK;
        failure=BB_ARENA_LAYOUT;
    }
    return shyt_dm_release(b->pool,off,len)==SHYT_DM_OK ? failure : BB_ARENA_CLEANUP;
}
#endif
