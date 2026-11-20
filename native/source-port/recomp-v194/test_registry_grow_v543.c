/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_grow_v543.h"
struct state { unsigned char data[112]; unsigned mode, calls; };
static int alloc(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    struct state *s=x;
    if (s->calls++ || owner!=0x4000 || n!=96 || s->mode==1) return 0;
    *b=(struct bb_vector_block_v541){s->data,sizeof s->data,s->mode==3?0x2000:0x3000};
    return 1;
}
static int release(void *x,uint64_t owner,uint64_t va) {
    struct state *s=x;
    return s->calls++==1 && owner==0x4000 && va==0x2000 && s->mode!=2;
}
static int warn(void *x) { (void)x; return 0; }
int main(void) {
    for (unsigned i=0;i<5;++i) {
        unsigned char h[40]={0}, orig[40], old[72]={0};
        const struct bb_vector_block_v541 backing={old,sizeof old,0x2000};
        struct state s={.mode=i}; memset(s.data,0xa5,sizeof s.data);
        const struct bb_growth_v543 g={&s,alloc,release};
        bb_arena_store_v527(h+8,0x2000); bb_arena_store_v527(h+16,0x2048);
        bb_arena_store_v527(h+24,0x2048); bb_arena_store_v527(h+32,0x4000);
        for (unsigned j=0;j<3;++j) {
            bb_arena_store_v527(old+24*j,1+j);
            bb_arena_store_v527(old+24*j+8,100+20*j);
            bb_arena_store_v527(old+24*j+16,105+20*j);
        }
        memcpy(orig,h,sizeof h);
        if (bb_registry_grow_v543(h,sizeof h,0x1000,&backing,i==4?1:9,110,5,warn,NULL,&g)!=
                (i==4?BB_INSERT_DUPLICATE:i?BB_INSERT_STOP:BB_INSERT_OK) ||
            s.calls!=(i==4?0u:i==1 || i==3?1u:2u)) return 1;
        if (i && memcmp(h,orig,sizeof h)) return 2;
        if (!i && (bb_vector_word_v541(h+8)!=0x3000 || bb_vector_word_v541(h+16)!=0x3060 ||
            bb_vector_word_v541(h+24)!=0x3060 || bb_vector_word_v541(s.data+24)!=9 ||
            memcmp(s.data,old,24) || memcmp(s.data+48,old+24,48) || s.data[96]!=0xa5)) return 3;
    }
    return 0;
}
