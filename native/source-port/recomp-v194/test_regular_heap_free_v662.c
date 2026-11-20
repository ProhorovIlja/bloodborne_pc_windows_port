/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "regular_heap_free_v662.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    static const unsigned order[][3]={{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
    _Alignas(16) unsigned char backing[4096];
    _Alignas(8) unsigned char heap[BB_HEAP_HEADER_V660], initial[sizeof heap];
    const uintptr_t h=(uintptr_t)heap;
    for (unsigned i=0;i<6;++i) {
        memset(backing,0x9b,sizeof backing);
        assert(bb_heap_seed_v660(heap,sizeof heap,backing,sizeof backing));
        memcpy(initial,heap,sizeof heap);
        void *p[3];
        for (unsigned j=0;j<3;++j) {
            p[j]=bb_heap_allocate_v661(heap,40,8);
            assert(p[j]);
            memset(p[j],0x41+(int)j,40);
        }
        assert(bb_heap_free_v662(heap,NULL));
        assert(!bb_heap_free_v662(heap,backing+1));
        for (unsigned j=0;j<3;++j) {
            assert(bb_heap_free_v662(heap,p[order[i][j]]));
            assert(bb_load_v661(h+32)==2-j);
        }
        assert(!memcmp(heap,initial,sizeof heap));
        assert(!bb_heap_free_v662(heap,p[0]));
        assert(bb_heap_allocate_v661(heap,bb_load_v661(h+24)-8,8)==p[0]);
        assert(bb_heap_free_v662(heap,p[0]));
        assert(!memcmp(heap,initial,sizeof heap));
    }
    /* Allocate leaving a header-only remainder, then coalesce it on free. */
    assert(bb_heap_seed_v660(heap,sizeof heap,backing,96));
    memcpy(initial,heap,sizeof heap);
    void *p=bb_heap_allocate_v661(heap,40,8);
    assert(p && bb_load_v661(h+24)==16 && !bb_load_v661(h));
    assert(bb_heap_free_v662(heap,p));
    assert(!memcmp(heap,initial,sizeof heap));
    puts("V662: six release orders, exhaustion/reuse, header-only coalescing passed");
}
