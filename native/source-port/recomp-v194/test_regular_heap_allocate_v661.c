/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "regular_heap_allocate_v661.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    static _Alignas(16) unsigned char backing[BB_HEAP_BACKING_V660+16];
    _Alignas(8) unsigned char heap[BB_HEAP_HEADER_V660], before[sizeof heap];
    const uintptr_t h=(uintptr_t)heap;
    for (unsigned skew=0;skew<16;++skew) {
        memset(backing,0xc4,sizeof backing);
        assert(bb_heap_seed_v660(heap,sizeof heap,backing+skew,BB_HEAP_BACKING_V660));
        const uintptr_t low=bb_load_v661(h+8), capacity=bb_load_v661(h+24);
        unsigned char *first=bb_heap_allocate_v661(heap,40,8);
        assert((uintptr_t)first==low && !(low&15));
        memset(first,0x53,40);
        assert(bb_load_v661(h+24)==capacity-48 && bb_load_v661(h+32)==1);
        assert((uintptr_t)bb_heap_allocate_v661(heap,24,16)==low+48);
        assert(first[39]==0x53 && bb_load_v661(h+24)==capacity-80);
        memcpy(before,heap,sizeof heap);
        assert(!bb_heap_allocate_v661(heap,1,3));
        assert(!bb_heap_allocate_v661(heap,1,32));
        assert(!bb_heap_allocate_v661(heap,UINTPTR_MAX,8));
        assert(!memcmp(before,heap,sizeof heap));
        assert((uintptr_t)bb_heap_allocate_v661(heap,capacity-88,0)==low+80);
        assert(!bb_load_v661(h) && !bb_load_v661(h+24) && bb_load_v661(h+32)==3);
        assert(!bb_heap_allocate_v661(heap,0,8));
    }
    puts("V661: first allocation (40/8), subsequent allocation, exact exhaustion and rejection passed");
}
