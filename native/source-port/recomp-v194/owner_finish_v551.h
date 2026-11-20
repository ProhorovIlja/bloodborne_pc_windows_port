/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_OWNER_FINISH_V551_H
#define BB_OWNER_FINISH_V551_H
#include "owner_registry_v540.h"
#include "registry_startup_v548.h"
#include "startup_memory_v478.h"

enum bb_finish_v551 { BB_FINISH_COLD, BB_FINISH_FAILED, BB_FINISH_READY };
struct bb_owner_finish_v551 {
    enum bb_finish_v551 state;
    unsigned char once;
    uint64_t owner;
};
/* Serialized post-publication startup. The heap mutex must be initialized
 * before entry. The owner and region bindings are immutable for this state.
 * A partially initialized heap is terminal; never use the retail once byte
 * as evidence that the registry is ready. */
static inline enum bb_finish_v551 bb_owner_finish_v551(struct bb_owner_finish_v551 *s,
        struct bb_owner_v539 *o,const struct bb_region_v478 *a,uint64_t heap_va,uint64_t heap_arena_va,
        const struct bb_registry_tls_v548 *tls,const struct bb_registry_driver_v548 *d,
        int (*header)(void *,uint64_t,size_t,size_t,struct bb_registry_block_v540 *),
        int (*warn)(void *)) {
    if (!s || !o || !a || !a->data || !a->base || a->size!=0x100000 ||
        a->base>UINT64_MAX-a->size || !d || !d->allocate || !d->release || !tls || !header || !warn)
        return BB_FINISH_FAILED;
    if (s->state!=BB_FINISH_COLD) return s->owner==o->va?s->state:BB_FINISH_FAILED;
    s->state=BB_FINISH_FAILED;
    s->owner=o->va;
    if (bb_owner_registry_seed_v549(o,o->va,heap_va,&s->once,a->data,heap_arena_va,d->ctx,header)!=BB_REGISTRY_SEEDED)
        return s->state;
    const uint64_t hva=bb_vector_word_v541(o->body+0x468);
    unsigned char *h=bb_memory_at_v478(a,hva,40);
    if (!h || bb_vector_word_v541(h+32)!=o->va) return s->state;
    struct bb_registry_alloc_v548 x={d,0};
    if (bb_vector_reserve_v541(h,40,hva,NULL,&x,bb_registry_allocate_v548,bb_registry_release_v548)!=BB_VEC_READY)
        return s->state;
    const uint64_t lo=bb_vector_word_v541(h+8);
    struct bb_vector_block_v541 b={bb_memory_at_v478(a,lo,768),768,lo};
    if (!b.data) return s->state;
    const struct bb_registry_result_v548 r=bb_registry_startup_v548(&o->lock,tls,h,40,hva,&b,
        o->va+0x458,a->base,a->size,warn,d->ctx,d);
    if (r.unlocked && r.insert==BB_INSERT_OK) s->state=BB_FINISH_READY;
    return s->state;
}
#endif
