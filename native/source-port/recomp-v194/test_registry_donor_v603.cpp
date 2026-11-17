/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "paleblood_v579/regular_heap.h"
using engine::regular_heap::Heap;
extern "C" void *bb_engine_regular_heap_allocate_02485730(Heap *,uint64_t);
extern "C" void bb_engine_regular_heap_free_024858a0(Heap *,void *);
extern "C" void *v603_allocate(void *p,size_t n) {
    return bb_engine_regular_heap_allocate_02485730(static_cast<Heap *>(p),n);
}
extern "C" void v603_release(void *p,void *b) {
    bb_engine_regular_heap_free_024858a0(static_cast<Heap *>(p),b);
}
