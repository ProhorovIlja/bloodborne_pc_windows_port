/* SPDX-License-Identifier: GPL-2.0-or-later
 * Adapted from Yharnam-Hunters/Paleblood@9b433c302e1a620e3021180f055c87886c6a133a, game/engine/regular_heap_free.cpp.
 */
#include <cstdlib>
#include "regular_heap.h"
using namespace engine::regular_heap;
// For live payloads from this heap, or null. The fast path assumes trusted
// arena metadata; obvious invalid inputs stop instead of logging and continuing.
extern "C" void bb_engine_regular_heap_free_024858a0(Heap *heap, void *payload) {
    if (!payload) return;
    const uintptr_t p=address_of(payload);
    if (p<heap->lowest_payload || p>=heap->highest_payload || (p&15)) std::abort();
    Block *block=reinterpret_cast<Block *>(p-block_header_size);
    const uintptr_t word=block->next_and_flags;
    if (!(word&block_in_use)) std::abort();
    Block *next=reinterpret_cast<Block *>(word&~block_flags);
    heap->available+=address_of(next)-address_of(block);
    --heap->allocation_count;
    Block *start=block;
    if (!(word&prev_in_use)) {
        start=block->prev;
        unlink_free_block(heap,start,block);
        block->next_and_flags=word-block_in_use;
    }
    const uintptr_t next_word=next->next_and_flags;
    Block *end;
    if (next_word&block_in_use) {
        start->next_and_flags=address_of(next)|prev_in_use;
        next->prev=start;
        next->next_and_flags=next_word-prev_in_use;
        end=next;
    } else {
        start->next_and_flags=next_word;
        end=reinterpret_cast<Block *>(next_word-prev_in_use);
        end->prev=start;
        unlink_free_block(heap,next,end);
    }
    push_free_block(heap,start,end);
}
