/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_grow_v543.h"
struct fixture { unsigned char bytes[32]; unsigned allocs, frees, fail; };
static int allocate(void *x,uint64_t owner,size_t size,struct bb_vector_block_v541 *b) {
    struct fixture *s=x;
    if (s->allocs++ || owner!=0x5000 || size!=24 || s->fail) return 0;
    *b=(struct bb_vector_block_v541){s->bytes,sizeof s->bytes,0x2000};
    return 1;
}
static int release(void *x,uint64_t owner,uint64_t va) {
    (void)owner; (void)va; ++((struct fixture *)x)->frees; return 0;
}
static int warn(void *x) { (void)x; return 0; }
int main(void) {
    for (unsigned mode=0;mode<3;++mode) {
        struct fixture s={.fail=mode==1}; memset(s.bytes,0xa5,sizeof s.bytes);
        unsigned char h[40]={0}, before[40];
        bb_arena_store_v527(h+32,0x5000);
        if (mode==2) bb_arena_store_v527(h+24,24);
        memcpy(before,h,sizeof h);
        const struct bb_growth_v543 g={&s,allocate,release};
        if (bb_registry_grow_v543(h,sizeof h,0x1000,NULL,7,50,5,warn,NULL,&g)!=
                (mode==2?BB_INSERT_INVALID:mode==1?BB_INSERT_STOP:BB_INSERT_OK) ||
            s.allocs!=(mode!=2) || s.frees || s.bytes[24]!=0xa5) return 1;
        if (mode && memcmp(h,before,sizeof h)) return 2;
        if (!mode && (bb_vector_word_v541(h+8)!=0x2000 || bb_vector_word_v541(h+16)!=0x2018 ||
            bb_vector_word_v541(h+24)!=0x2018 || bb_vector_word_v541(s.bytes)!=7 ||
            bb_vector_word_v541(s.bytes+8)!=50 || bb_vector_word_v541(s.bytes+16)!=55)) return 3;
    }
    return 0;
}
