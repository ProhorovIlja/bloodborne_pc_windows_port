/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_OWNER_REGISTRY_V540_H
#define BB_OWNER_REGISTRY_V540_H
#include "factory_owner_v539.h"
#include "arena_seed_v527.h"

enum bb_registry_v540 { BB_REGISTRY_INVALID, BB_REGISTRY_ARENA,
    BB_REGISTRY_ALLOC, BB_REGISTRY_SEEDED, BB_REGISTRY_ALREADY };
struct bb_registry_block_v540 { unsigned char *data; size_t size; uint64_t va; };
/* Serialized post-publication prefix only. The caller supplies an attested
 * owner and disjoint host buffers and binds the allocator. SEEDED means the
 * registry header exists, not that the factory is ready to return. A failure
 * after setting the once byte is terminal; the caller must not retry. */
/* heap_va controls the links in the heap metadata. It may differ from
 * published only when the metadata is private to the host allocator. */
static inline enum bb_registry_v540 bb_owner_registry_seed_v549(
        struct bb_owner_v539 *owner, uint64_t published, uint64_t heap_va, unsigned char *once,
        unsigned char *arena, uint64_t arena_va, void *ctx,
        int (*allocate)(void *,uint64_t,size_t,size_t,struct bb_registry_block_v540 *)) {
    const size_t extent=0x100000;
    if (!owner || !owner->body || !owner->lock.live || owner->lock.held ||
        !published || published!=owner->va || published>UINT64_MAX-0x48c ||
        !heap_va || !once || !arena || !allocate) return BB_REGISTRY_INVALID;
    if (*once) return BB_REGISTRY_ALREADY;
    *once=1;
    unsigned char *p=owner->body;
    if (!bb_arena_seed_v527(p,0x48c,0,heap_va,arena,extent,arena_va)) return BB_REGISTRY_ARENA;
    bb_factory_put_v538(p+0x488,0x1000,4);
    struct bb_registry_block_v540 b={0};
    if (!allocate(ctx,published+0x458,40,8,&b) || !b.data || b.size<40 ||
        !b.va || (b.va&7) || b.va>UINT64_MAX-40) {
        bb_factory_put_v538(p+0x468,0,8);
        return BB_REGISTRY_ALLOC;
    }
    for (size_t i=8;i<32;i+=8) bb_factory_put_v538(b.data+i,0,8);
    bb_factory_put_v538(b.data+32,published,8);
    bb_factory_put_v538(p+0x468,b.va,8);
    return BB_REGISTRY_SEEDED;
}
static inline enum bb_registry_v540 bb_owner_registry_v540(
        struct bb_owner_v539 *owner, uint64_t published, unsigned char *once,
        unsigned char *arena, uint64_t arena_va, void *ctx,
        int (*allocate)(void *,uint64_t,size_t,size_t,struct bb_registry_block_v540 *)) {
    return bb_owner_registry_seed_v549(owner,published,published,once,arena,arena_va,ctx,allocate);
}
#endif
