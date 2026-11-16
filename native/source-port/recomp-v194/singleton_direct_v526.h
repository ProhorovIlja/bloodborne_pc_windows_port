/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_SINGLETON_DIRECT_V526_H
#define BB_SINGLETON_DIRECT_V526_H
#include "native_direct_memory_v411.h"

/* Native startup's size -> allocate -> map transaction. Offset zero is
 * valid. Mapping is CPU-only host storage, never a guest VA or code target.
 * Caller owns the pool and must release a successful result with V411.
 * This is not the remainder of the singleton initializer. */
struct bb_singleton_memory_v526 { uint64_t offset; void *storage; };
enum bb_singleton_memory_status_v526 {
    BB_DM526_INVALID, BB_DM526_ALLOC_FAILED, BB_DM526_MAP_FAILED,
    BB_DM526_ROLLBACK_FAILED, BB_DM526_READY
};
static inline enum bb_singleton_memory_status_v526 bb_singleton_memory_v526(
        ShytDmPool *pool, const ShytDmBackend *backend, uint64_t bytes,
        uint64_t align, struct bb_singleton_memory_v526 *out) {
    if (!pool || !pool->limit || pool->limit>INT64_MAX || !backend ||
        !backend->map || !backend->unmap || !out || !bytes ||
        bytes%SHYT_DM_PAGE || align%SHYT_DM_PAGE) return BB_DM526_INVALID;
    uint64_t offset;
    if (shyt_dm_allocate(pool,0,(int64_t)pool->limit,bytes,align,0,&offset)!=SHYT_DM_OK)
        return BB_DM526_ALLOC_FAILED;
    void *storage=NULL;
    if (shyt_dm_map(pool,backend,offset,bytes,align,3,0,&storage)!=SHYT_DM_OK)
        return shyt_dm_release(pool,offset,bytes)==SHYT_DM_OK ?
            BB_DM526_MAP_FAILED : BB_DM526_ROLLBACK_FAILED;
    *out=(struct bb_singleton_memory_v526){offset,storage};
    return BB_DM526_READY;
}
#endif
