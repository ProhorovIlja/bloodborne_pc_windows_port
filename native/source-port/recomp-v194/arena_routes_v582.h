/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_ROUTES_V582_H
#define BB_ARENA_ROUTES_V582_H
#include "arena_slots_v581.h"

enum class BbArenaStatusV582 { complete, invalid, lock_failed, unlock_failed, unsupported };
struct BbArenaResultV582 { BbArenaStatusV582 status; void *payload; };
/* Offsets label retail call sites, not the layout of a host vtable.
 * Only live payloads from this arena (or null) may be freed. Foreign
 * pointers are reported, not dispatched to the unported external path. */
static inline BbArenaResultV582 bb_arena_route_v582(BbArenaV581 a,unsigned slot,
    void *payload,uint64_t n,uint64_t align) {
    using S=BbArenaStatusV582;
    if (!a.heap || !a.mutex || !a.lock || !a.unlock) return {S::invalid,nullptr};
    const bool freeing=slot==0x70 || slot==0xa0;
    const bool aligned=slot==0x58 || slot==0x88;
    if (!freeing && !aligned && slot!=0x50 && slot!=0x80) return {S::unsupported,nullptr};
    const unsigned depth=(slot==0x80 || slot==0x88 || slot==0xa0)?2:1;
    unsigned held=0;
    while (held<depth && a.lock(a.mutex,-1)) ++held;
    S status=held==depth ? S::complete : S::lock_failed;
    void *out=nullptr;
    if (status==S::complete) {
        if (freeing) {
            const uintptr_t p=reinterpret_cast<uintptr_t>(payload);
            if (p) {
                const uintptr_t first=reinterpret_cast<uintptr_t>(a.heap->first_block);
                if (!first || p<first || p-first>=a.heap->capacity ||
                    p<a.heap->lowest_payload || p>=a.heap->highest_payload || (p&15))
                    status=S::unsupported;
                else bb_engine_regular_heap_free_024858a0(a.heap,payload);
            }
        } else if (aligned) out=bb_engine_regular_heap_allocate_aligned_02485a60(a.heap,n,align);
        else out=bb_engine_regular_heap_allocate_02485730(a.heap,n);
    }
    while (held) {
        --held;
        if (!a.unlock(a.mutex)) return {S::unlock_failed,nullptr};
    }
    return {status,out};
}
#endif
