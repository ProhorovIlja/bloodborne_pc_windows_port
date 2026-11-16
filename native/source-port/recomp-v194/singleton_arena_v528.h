/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_SINGLETON_ARENA_V528_H
#define BB_SINGLETON_ARENA_V528_H
#include "singleton_direct_v526.h"
#include "arena_seed_v527.h"

enum bb_arena_status_v528 {
    BB_ARENA_INVALID, BB_ARENA_ALLOC, BB_ARENA_MAP, BB_ARENA_ROLLBACK, BB_ARENA_READY
};
/* Success-path startup bridge only. A caller-owned mapping policy supplies
 * arena_va and must subsequently resolve it to result.storage. A host
 * pointer never goes into the object. No publication or retry here. */
static inline enum bb_arena_status_v528 bb_singleton_arena_v528(
        ShytDmPool *pool, const ShytDmBackend *backend,
        unsigned char *obj, size_t n, size_t bitmap, size_t mapping,
        uint64_t obj_va, uint64_t arena_va, size_t bytes, uint64_t align,
        struct bb_singleton_memory_v526 *out) {
    enum { metadata=40+64*16+24, mapping_words=24 };
    if (!obj || !out || n<mapping_words || mapping>n-mapping_words ||
        n<metadata || bitmap>n-metadata ||
        (mapping<bitmap+metadata && bitmap<mapping+mapping_words) ||
        !arena_va || (align && arena_va%align) ||
        arena_va%SHYT_DM_PAGE || bytes>UINT64_MAX-arena_va ||
        n>UINT64_MAX-obj_va || ((obj_va+bitmap)&7) ||
        (obj_va<arena_va+bytes && arena_va<obj_va+n)) return BB_ARENA_INVALID;
    struct bb_singleton_memory_v526 result;
    switch (bb_singleton_memory_v526(pool,backend,bytes,align,&result)) {
    case BB_DM526_INVALID: return BB_ARENA_INVALID;
    case BB_DM526_ALLOC_FAILED: return BB_ARENA_ALLOC;
    case BB_DM526_MAP_FAILED: return BB_ARENA_MAP;
    case BB_DM526_ROLLBACK_FAILED: return BB_ARENA_ROLLBACK;
    case BB_DM526_READY: break;
    default: return BB_ARENA_INVALID;
    }
    if (!bb_arena_seed_v527(obj,n,bitmap,obj_va,result.storage,bytes,arena_va))
        return shyt_dm_release(pool,result.offset,bytes)==SHYT_DM_OK ?
            BB_ARENA_INVALID : BB_ARENA_ROLLBACK;
    bb_arena_store_v527(obj+mapping,arena_va);
    bb_arena_store_v527(obj+mapping+8,result.offset);
    bb_arena_store_v527(obj+mapping+16,bytes);
    *out=result;
    return BB_ARENA_READY;
}
#endif
