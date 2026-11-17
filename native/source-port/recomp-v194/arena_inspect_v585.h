/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_INSPECT_V585_H
#define BB_ARENA_INSPECT_V585_H
#include "arena_slots_v581.h"
#include <cstring>

struct BbInspectV585 { BbAllocStatusV581 status; uint64_t value; };
/* Read-only retail slot subset. Caller serializes all reads with arena
 * mutation; only readiness takes the internal lock in the original.
 * Heap metadata and live payload provenance are trusted. */
static inline BbInspectV585 bb_arena_inspect_v585(BbArenaV581 a,unsigned slot,
    const void *payload=nullptr,const void *mapped_base_word=nullptr) {
    using S=BbAllocStatusV581;
    using namespace engine::regular_heap;
    if (!a.heap) return {S::invalid,0};
    auto *h=a.heap;
    switch (slot) {
    case 0x10: return {S::complete,0x401};
    case 0x28: return {S::complete,h->capacity};
    case 0x30: return {S::complete,h->available};
    case 0x40: return {S::complete,h->allocation_count};
    case 0x38: {
        uint64_t best=0;
        if (h->nonempty_lists) {
            auto *s=list_sentinel(h,list_index(h->nonempty_lists));
            for (auto *b=s->list_next;b!=s;b=b->list_next) {
                const uint64_t n=(b->next_and_flags&~block_flags)-address_of(b)-8;
                if (n>best) best=n;
            }
        }
        return {S::complete,best};
    }
    case 0x48: {
        const uintptr_t p=address_of(payload);
        if (!p || (p&15) || p<h->lowest_payload || p>=h->highest_payload)
            return {S::invalid,0};
        uintptr_t word;
        std::memcpy(&word,static_cast<const unsigned char *>(payload)-8,sizeof word);
        const uintptr_t end=word&~block_flags;
        if (!(word&block_in_use) || end<=p || end>address_of(h->end_block)) return {S::invalid,0};
        return {S::complete,end-p+8};
    }
    case 0xa8: {
        if (!mapped_base_word || !a.mutex || !a.lock || !a.unlock) return {S::invalid,0};
        if (!a.lock(a.mutex,-1)) return {S::lock_failed,0};
        uint64_t base;
        // Native arena prefix owns the mapped-base word, outside Heap.
        std::memcpy(&base,mapped_base_word,sizeof base);
        const bool ready=base && h->lowest_payload;
        return a.unlock(a.mutex) ? BbInspectV585{S::complete,ready} : BbInspectV585{S::unlock_failed,0};
    }
    default: return {S::invalid,0};
    }
}
#endif
