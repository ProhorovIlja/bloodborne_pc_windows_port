/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_reserve_v541.h"
struct fixture { unsigned char fresh[776]; unsigned calls, mode; };
static int alloc(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    struct fixture *s=x;
    if (s->calls++ || owner!=0x9000 || n!=768 || s->mode==1) return 0;
    *out=(struct bb_vector_block_v541){s->fresh,sizeof s->fresh,s->mode==4?0x2000:0x3000};
    return 1;
}
static int release(void *x,uint64_t owner,uint64_t old) {
    struct fixture *s=x;
    return s->calls++==1 && owner==0x9000 && old==0x2000 &&
        s->fresh[0]==0x51 && s->mode!=2;
}
int main(void) {
    for (unsigned mode=0;mode<6;++mode) {
        unsigned char h[48]={0}, before[48], backing[768];
        memset(backing,0x51,sizeof backing);
        struct fixture f={.mode=mode}; memset(f.fresh,0xa5,sizeof f.fresh);
        bb_arena_store_v527(h+8,0x2000); bb_arena_store_v527(h+16,0x2018+(mode==5));
        bb_arena_store_v527(h+24,0x2000+(mode==3?768:48)); bb_arena_store_v527(h+32,0x9000);
        memcpy(before,h,sizeof h);
        const struct bb_vector_block_v541 old={backing,sizeof backing,0x2000};
        const enum bb_vector_v541 want[]={BB_VEC_READY,BB_VEC_ALLOC,BB_VEC_RELEASE,
            BB_VEC_UNCHANGED,BB_VEC_ALLOC,BB_VEC_INVALID};
        if (bb_vector_reserve_v541(h,sizeof h,0x1000,&old,&f,alloc,release)!=want[mode] ||
            f.calls!=(mode==0 || mode==2?2u:mode==1 || mode==4?1u:0u)) return 1;
        if (mode && memcmp(h,before,sizeof h)) return 2;
        if (!mode && (bb_vector_word_v541(h+8)!=0x3000 || bb_vector_word_v541(h+16)!=0x3018 ||
            bb_vector_word_v541(h+24)!=0x3300 || bb_vector_word_v541(h+32)!=0x9000)) return 3;
        if ((!mode || mode==2) && (memcmp(f.fresh,backing,24) || f.fresh[24]!=0xa5 || f.fresh[768]!=0xa5)) return 4;
    }
    return 0;
}
