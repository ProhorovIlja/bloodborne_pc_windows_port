/* SPDX-License-Identifier: GPL-2.0-or-later
 * Adapted from Yharnam-Hunters/Paleblood@9b433c302e1a620e3021180f055c87886c6a133a, game/engine/regular_heap_allocate_aligned.cpp.
 */
#include "regular_heap.h"
using namespace engine::regular_heap;
extern "C" void *bb_engine_regular_heap_allocate_02485730(Heap *,uint64_t);
namespace {
uintptr_t align_up(uintptr_t p,uint64_t a) { return (p+(a-1))&(0-a); }
struct Choice { Block *block; int index; };
Choice fit(Heap *h,int first,uint64_t size,uint64_t a) {
    constexpr uint64_t overlap=offsetof(Block,next_and_flags);
    for (uint64_t lists=h->nonempty_lists&(~uint64_t{0}<<first);lists;lists&=lists-1) {
        const int i=__builtin_ctzll(lists);
        Block *s=list_sentinel(h,i);
        for (Block *b=s->list_next;b!=s;b=b->list_next) {
            const uintptr_t next=b->next_and_flags-prev_in_use;
            const uintptr_t aligned=align_up(address_of(b)+block_header_size,a);
            if (next>aligned && next-aligned+overlap>=size-overlap) return {b,i};
        }
    }
    return {nullptr,0};
}
}
extern "C" void *bb_engine_regular_heap_allocate_aligned_02485a60(Heap *h,uint64_t request,uint64_t a) {
    if ((a&(a-1)) || h->available<request) return nullptr;
    if (a<=16) return bb_engine_regular_heap_allocate_02485730(h,request);
    const uint64_t size=block_size_for(request);
    Choice c{nullptr,0};
    if (a<=0x3ff) {
        const uint64_t larger=h->nonempty_lists&(~uint64_t{1}<<list_index(a+size));
        if (larger) {
            c.index=__builtin_ctzll(larger);
            c.block=list_sentinel(h,c.index)->list_next;
        }
    }
    if (!c.block) c=fit(h,list_index(size),size,a);
    if (!c.block) return nullptr;
    Block *b=c.block;
    take_from_list(h,b,c.index);
    book_allocation(h,size);
    const uintptr_t word=b->next_and_flags;
    Block *next=reinterpret_cast<Block *>(word-prev_in_use);
    const uintptr_t payload=address_of(b)+block_header_size;
    if (payload&(a-1)) {
        const uintptr_t aligned=align_up(payload,a);
        Block *allocated=reinterpret_cast<Block *>(aligned-block_header_size);
        Block *rest=reinterpret_cast<Block *>(address_of(allocated)+size);
        b->next_and_flags=address_of(allocated)|prev_in_use;
        allocated->prev=b;
        allocated->next_and_flags=address_of(rest)|block_in_use;
        if (next==rest) next->next_and_flags+=prev_in_use;
        else free_rest(h,rest,word);
        if (address_of(allocated)!=payload) push_free_block(h,b,allocated);
        return reinterpret_cast<void *>(aligned);
    }
    Block *rest=reinterpret_cast<Block *>(address_of(b)+size);
    if (address_of(next)<=address_of(rest)) {
        next->next_and_flags+=prev_in_use;
        b->next_and_flags=word+block_in_use;
    } else {
        b->next_and_flags=address_of(rest)|prev_in_use|block_in_use;
        free_rest(h,rest,word);
    }
    return reinterpret_cast<void *>(payload);
}
