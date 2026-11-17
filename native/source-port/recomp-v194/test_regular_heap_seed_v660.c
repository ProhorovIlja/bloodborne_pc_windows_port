/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "regular_heap_seed_v660.h"
#include <assert.h>
#include <stdio.h>

static uintptr_t word(const unsigned char *p) {
    uintptr_t v=0;
    memcpy(&v,p,8);
    return v;
}
int main(void) {
    static _Alignas(16) unsigned char backing[BB_HEAP_BACKING_V660+16];
    _Alignas(8) unsigned char heap[BB_DEPENDENCY_BYTES_V659];
    for (unsigned skew=0;skew<16;++skew) {
        memset(heap,0x9a,sizeof heap);
        memset(backing,0x5a,sizeof backing);
        assert(bb_dependency_seed_v659(heap,sizeof heap,(struct bb_dependency_tables_v659){1,2,3}));
        unsigned char tail[sizeof heap-BB_HEAP_HEADER_V660];
        memcpy(tail,heap+BB_HEAP_HEADER_V660,sizeof tail);
        assert(bb_heap_seed_v660(heap,sizeof heap,backing+skew,BB_HEAP_BACKING_V660));
        const uintptr_t low=word(heap+8), high=word(heap+16);
        const uintptr_t first=word(heap+0x428), end=word(heap+0x430);
        assert(!(low&15) && !(high&15) && first+16==low && end+16==high);
        assert(first+8>=(uintptr_t)backing+skew && high<=(uintptr_t)backing+skew+BB_HEAP_BACKING_V660);
        assert(word(heap+24)==high-low && word(heap+0x438)==high-low && !word(heap+32));
        assert(word(heap)==(UINT64_C(1)<<19));
        assert(word((const unsigned char *)first+8)==(end|2));
        assert(word((const unsigned char *)end)==first && word((const unsigned char *)end+8)==(first|1));
        for (unsigned i=0;i<64;++i) {
            const unsigned char *list=heap+0x28+16*i;
            const uintptr_t link=i==19 ? first : (uintptr_t)(list-16);
            assert(word(list)==link && word(list+8)==link);
        }
        assert(!memcmp(tail,heap+BB_HEAP_HEADER_V660,sizeof tail));
        assert(!bb_heap_seed_v660(heap,sizeof heap,heap,64) && word(heap+8)==low);
        assert(!bb_heap_seed_v660(heap,sizeof heap,backing+skew,32));
        for (size_t i=0;i<BB_HEAP_HEADER_V660;++i) assert(!heap[i]);
        assert(!memcmp(tail,heap+BB_HEAP_HEADER_V660,sizeof tail));
    }
    puts("V660: 16 alignments, 64 lists each, overlap and short-range checks passed");
    return 0;
}
