/* SPDX-License-Identifier: GPL-2.0-or-later
 * Adapted from Yharnam-Hunters/Paleblood game/engine/regular_heap_check_block.cpp
 * upstream blob 4e0db0bc5d27e607ff58794c49b4f46bf8f57cd2.
 */
#ifndef BB_ARENA_CHECK_V589_H
#define BB_ARENA_CHECK_V589_H
#include "paleblood_v579/regular_heap.h"
#include <cstring>
struct BbBlockCheckV589 { bool accepted; uintptr_t bad_word; };
/* Retail slot +0xd0. Arena bounds and sentinel storage must be trusted
 * and serialized by the caller. Invalid input stops before reading it. */
static inline BbBlockCheckV589 bb_arena_check_v589(engine::regular_heap::Heap *h,uintptr_t p) {
    using namespace engine::regular_heap;
    if (!h || (p&15)) return {false,0};
    const uintptr_t first=address_of(h->first_block),end=address_of(h->end_block);
    if (!first || (first&15) || (end&15) || end<first || end-first<16 ||
        p<first+16 || p>end || end>UINTPTR_MAX-16) return {false,0};
    const auto read=[](uintptr_t at) {
        uintptr_t word;
        std::memcpy(&word,reinterpret_cast<const void *>(at),sizeof word);
        return word;
    };
    const auto forward=[=](uintptr_t from,uintptr_t to) {
        return !(to&15) && to>=first && to<=end && to>from;
    };
    const uintptr_t b=p-16, word=read(b+8), next=word&~block_flags;
    if (!forward(b,next)) return {true,b+8};
    const uintptr_t following=read(next+8);
    if (next!=end && !forward(next,following&~block_flags)) return {true,next+8};
    if (word&block_in_use) return {true,(following&prev_in_use)?0:next+8};
    if (read(next)!=b) return {true,next};
    if ((following&block_flags)!=block_in_use) return {true,next+8};
    if (next==p) return {true,0};
    const uintptr_t sentinel=address_of(list_sentinel(h,list_index(next-b)));
    const auto valid_link=[=](uintptr_t at) {
        return at==sentinel || (!(at&15) && at>=first && at<end && end-at>=32);
    };
    const uintptr_t prev=read(b+16), after=read(b+24);
    if (!valid_link(prev)) return {true,b+16};
    if (!valid_link(after)) return {true,b+24};
    if (read(prev+24)!=b) return {true,prev+24};
    if (read(after+16)!=b) return {true,after+16};
    return {true,0};
}
#endif
