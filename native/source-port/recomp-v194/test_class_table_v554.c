/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_table_v554.h"
struct state { unsigned char data[0x4008]; unsigned calls,fail; };
static int alloc(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    struct state *s=x;
    if (s->calls++ || owner!=0x2000 || n!=0x4000 || s->fail) return 0;
    *b=(struct bb_vector_block_v541){s->data,sizeof s->data,0x3000};
    return 1;
}
static int drop(void *x,uint64_t owner,uint64_t va) {
    struct state *s=x; return s->calls++==1 && owner==0x2000 && va==0x8000;
}
static int grow_alloc(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    struct state *s=x;
    if (s->calls++ || owner!=0x2000 || n!=128) return 0;
    *b=(struct bb_vector_block_v541){s->data,sizeof s->data,s->fail?0x8000:0x3000};
    return 1;
}
static int test_grow(void) {
    unsigned char h[40]={0},old[96]={0},before[40];
    const struct bb_vector_block_v541 b={old,sizeof old,0x8000};
    struct state s={0}; memset(s.data,0xa5,sizeof s.data);
    bb_arena_store_v527(h+8,0x8000); bb_arena_store_v527(h+16,0x8060);
    bb_arena_store_v527(h+24,0x8060); bb_arena_store_v527(h+32,0x2000);
    for (unsigned i=0;i<3;++i) {
        bb_arena_store_v527(old+32*i,10+i);
        bb_arena_store_v527(old+32*i+24,i+1);
    }
    const uint64_t row[]={99,98,97,2};
    memcpy(before,h,sizeof h); s.fail=1;
    if (bb_class_insert_v554(h,40,0x1000,&b,row,&s,grow_alloc,drop)!=BB_CLASS_STOP ||
        s.calls!=1 || memcmp(h,before,sizeof h) || s.data[0]!=0xa5) return 1;
    s.calls=s.fail=0;
    if (bb_class_insert_v554(h,40,0x1000,&b,row,&s,grow_alloc,drop)!=BB_CLASS_OK ||
        s.calls!=2 || bb_vector_word_v541(h+8)!=0x3000 || bb_vector_word_v541(h+16)!=0x3080 ||
        bb_vector_word_v541(h+24)!=0x3080 || memcmp(s.data,old,64) ||
        bb_vector_word_v541(s.data+64)!=99 || bb_vector_word_v541(s.data+88)!=2 ||
        memcmp(s.data+96,old+64,32) || s.data[128]!=0xa5) return 1;
    return 0;
}
int main(void) {
    if (test_grow()) return 6;
    unsigned char h[40]={0},old[32]={0};
    const struct bb_vector_block_v541 b={old,sizeof old,0x8000};
    struct state s={0}; s.data[0x4000]=0x5a;
    uint64_t row[]={1,2,3,4};
    bb_arena_store_v527(h+32,0x2000);
    bb_arena_store_v527(h+8,0x8000); bb_arena_store_v527(h+16,0x8000);
    bb_arena_store_v527(h+24,0x8020);
    if (bb_class_insert_v554(h,40,0x1000,&b,row,&s,alloc,drop)!=BB_CLASS_OK || s.calls!=2 ||
        bb_vector_word_v541(h+8)!=0x3000 || bb_vector_word_v541(h+24)!=0x7000 ||
        bb_vector_word_v541(h+16)!=0x3020 || s.data[0x4000]!=0x5a) return 1;
    const struct bb_vector_block_v541 c={s.data,sizeof s.data,0x3000};
    row[0]=5;
    if (bb_class_insert_v554(h,40,0x1000,&c,row,&s,alloc,drop)!=BB_CLASS_OK || s.calls!=2 ||
        bb_vector_word_v541(s.data)!=1 || bb_vector_word_v541(s.data+32)!=5) return 2;
    row[0]=6; row[3]=0;
    if (bb_class_insert_v554(h,40,0x1000,&c,row,&s,alloc,drop)!=BB_CLASS_OK ||
        bb_vector_word_v541(s.data)!=6 || bb_vector_word_v541(s.data+32)!=1) return 3;
    bb_arena_store_v527(h+24,0x3060);
    unsigned char before[40]; memcpy(before,h,sizeof before);
    if (bb_class_insert_v554(h,40,0x1000,&c,row,&s,alloc,drop)!=BB_CLASS_STOP || s.calls!=3 ||
        memcmp(h,before,sizeof h)) return 4;
    memset(h+8,0,24); s.calls=0; s.fail=1;
    if (bb_class_insert_v554(h,40,0x1000,NULL,row,&s,alloc,drop)!=BB_CLASS_STOP ||
        bb_vector_word_v541(h+8) || bb_vector_word_v541(h+16) || bb_vector_word_v541(h+24)) return 5;
    bb_arena_store_v527(h+24,32);
    return bb_class_insert_v554(h,40,0x1000,NULL,row,&s,alloc,drop)!=BB_CLASS_INVALID;
}
