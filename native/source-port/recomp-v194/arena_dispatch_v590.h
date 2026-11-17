/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_DISPATCH_V590_H
#define BB_ARENA_DISPATCH_V590_H
#include "arena_resize_v586.h"
#include "arena_external_v584.h"
#include "arena_meta_v587.h"
#include "arena_control_v588.h"
#include "arena_check_v589.h"
#include "arena_seed_v577.h"

struct BbArenaDispatchV590 {
    BbArenaV581 arena;
    const unsigned char *object;
    BbExternalV584 *external;
    const BbMutexControlV588 *control;
};
struct BbArenaReplyV590 { BbArenaStatusV582 status; uint64_t value; };
/* Dispatch by labels from the retail table, never through its function pointers.
 * The static singleton cannot be deleted. Foreign realloc remains unsupported.
 * Callers serialize reads and keep the bound object, heap and mutex alive. */
static inline BbArenaReplyV590 bb_arena_dispatch_v590(const BbArenaDispatchV590 &x,
    unsigned slot,void *p=nullptr,uint64_t n=0,uint64_t alignment=0) {
    using S=BbArenaStatusV582;
    if (!x.object || !x.arena.heap) return {S::invalid,0};
    switch (slot) {
    case 0x08: return {S::unsupported,0};
    case 0x20: return bb_arena_kind_v587(p,n) ? BbArenaReplyV590{S::complete,reinterpret_cast<uintptr_t>(p)}
                                             : BbArenaReplyV590{S::invalid,0};
    case 0xb0: return {S::complete,bb_arena_header_live_v587(x.arena.heap,reinterpret_cast<uintptr_t>(p))};
    case 0xd0: {
        const auto y=bb_arena_check_v589(x.arena.heap,reinterpret_cast<uintptr_t>(p));
        return {y.accepted?S::complete:S::invalid,y.bad_word};
    }
    case 0x00: case 0x18: case 0x78: case 0xb8: case 0xc0: case 0xc8: {
        const auto y=bb_arena_control_v588(slot,x.control);
        return {y.state==BbControlStateV588::complete?S::complete:S::invalid,
                static_cast<uint32_t>(y.value)};
    }
    case 0x10: case 0x28: case 0x30: case 0x38: case 0x40: case 0x48: case 0xa8: {
        const auto y=bb_arena_inspect_v585(x.arena,slot,p,x.object+0x468);
        switch (y.status) {
        case BbAllocStatusV581::complete: return {S::complete,y.value};
        case BbAllocStatusV581::lock_failed: return {S::lock_failed,0};
        case BbAllocStatusV581::unlock_failed: return {S::unlock_failed,0};
        default: return {S::invalid,0};
        }
    }
    case 0x50: case 0x58: case 0x70: case 0x80: case 0x88: case 0xa0: {
        const auto y=bb_arena_route_v582(x.arena,slot,p,n,alignment,
            x.external?bb_external_query_v584:nullptr,x.external,
            x.external?bb_external_free_v584:nullptr);
        return {y.status,reinterpret_cast<uintptr_t>(y.payload)};
    }
    case 0x60: case 0x68: case 0x90: case 0x98: {
        const auto y=bb_arena_resize_v586(x.arena,slot,p,n,alignment);
        return {y.status,reinterpret_cast<uintptr_t>(y.payload)};
    }
    default: return {S::unsupported,0};
    }
}
#endif
