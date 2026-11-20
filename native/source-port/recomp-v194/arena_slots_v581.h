/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_SLOTS_V581_H
#define BB_ARENA_SLOTS_V581_H
#include "paleblood_v579/regular_heap.h"
using BbHeapV581=engine::regular_heap::Heap;
extern "C" void *bb_engine_regular_heap_allocate_02485730(BbHeapV581 *,uint64_t);
extern "C" void *bb_engine_regular_heap_allocate_aligned_02485a60(BbHeapV581 *,uint64_t,uint64_t);
extern "C" void bb_engine_regular_heap_free_024858a0(BbHeapV581 *,void *);
struct BbArenaV581 {
    BbHeapV581 *heap;
    void *mutex;
    bool (*lock)(void *,int32_t);
    bool (*unlock)(void *);
};
enum class BbAllocStatusV581 { invalid, lock_failed, unlock_failed, complete };
struct BbAllocV581 { BbAllocStatusV581 status; void *payload; };
/* Typed subset for translated callers, NOT the PS4 vtable layout.
 * On unlock failure the arena is terminal: the allocation may have mutated it. */
static inline BbAllocV581 bb_arena_call_v581(BbArenaV581 a,uint64_t n,uint64_t alignment,bool aligned) {
    if (!a.heap || !a.mutex || !a.lock || !a.unlock) return {BbAllocStatusV581::invalid,nullptr};
    if (!a.lock(a.mutex,-1)) return {BbAllocStatusV581::lock_failed,nullptr};
    void *p=aligned ? bb_engine_regular_heap_allocate_aligned_02485a60(a.heap,n,alignment)
                    : bb_engine_regular_heap_allocate_02485730(a.heap,n);
    if (!a.unlock(a.mutex)) return {BbAllocStatusV581::unlock_failed,nullptr};
    return {BbAllocStatusV581::complete,p};
}
struct BbArenaSlotsV581 {
    BbAllocV581 (*allocate)(BbArenaV581,uint64_t);            // retail +0x50
    BbAllocV581 (*aligned)(BbArenaV581,uint64_t,uint64_t);    // retail +0x58
};
static inline const BbArenaSlotsV581 *bb_arena_slots_v581() {
    static const BbArenaSlotsV581 slots={
        [](BbArenaV581 a,uint64_t n){return bb_arena_call_v581(a,n,0,false);},
        [](BbArenaV581 a,uint64_t n,uint64_t align){return bb_arena_call_v581(a,n,align,true);}
    };
    return &slots;
}
#endif
