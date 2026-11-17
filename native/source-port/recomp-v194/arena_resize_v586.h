/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_RESIZE_V586_H
#define BB_ARENA_RESIZE_V586_H
#include "arena_routes_v582.h"
#include "arena_inspect_v585.h"

/* Owned live payloads only. Foreign realloc and external allocation flags
 * are intentionally not implemented here. Callers own payload provenance.
 * An unlock failure is terminal, including after heap mutation. */
static inline BbArenaResultV582 bb_arena_resize_v586(BbArenaV581 a,unsigned slot,
    void *payload,uint64_t n,uint64_t align) {
    using S=BbArenaStatusV582;
    const bool aligned=slot==0x68 || slot==0x98;
    const unsigned outer=slot==0x90 || slot==0x98 ? 2 : 1;
    if (!a.heap || !a.mutex || !a.lock || !a.unlock) return {S::invalid,nullptr};
    if (!aligned && slot!=0x60 && slot!=0x90) return {S::unsupported,nullptr};
    unsigned held=0;
    while (held<outer && a.lock(a.mutex,-1)) ++held;
    BbArenaResultV582 result{S::lock_failed,nullptr};
    if (held==outer) {
        const auto old=payload ? bb_arena_inspect_v585(a,0x48,payload)
                               : BbInspectV585{BbAllocStatusV581::complete,0};
        if (old.status!=BbAllocStatusV581::complete) result={S::unsupported,nullptr};
        else if (!n) result=bb_arena_route_v582(a,0x70,payload,0,0);
        else {
            result=bb_arena_route_v582(a,aligned?0x58:0x50,nullptr,n,align);
            if (result.status==S::complete && result.payload && payload) {
                std::memcpy(result.payload,payload,static_cast<size_t>(n<old.value?n:old.value));
                const auto dropped=bb_arena_route_v582(a,0x70,payload,0,0);
                if (dropped.status!=S::complete) result={dropped.status,nullptr};
            }
        }
    }
    if (result.status==S::unlock_failed) return result;
    while (held--) if (!a.unlock(a.mutex)) return {S::unlock_failed,nullptr};
    return result;
}
#endif
