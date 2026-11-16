/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_sort_v556.h"

#include "class_secondary_v557.h"
struct fixture557 {
    unsigned char buf[2][768*16];
    unsigned active, calls, allocs, frees, fail_key, fail_alloc, fail_release;
};
static uint64_t va557(unsigned slot) { return UINT64_C(0x100020000)+slot*UINT64_C(0x10000); }
static int alloc557(void *v,uint64_t owner,size_t bytes,struct bb_vector_block_v541 *b) {
    struct fixture557 *f=v;
    ++f->allocs;
    if (owner!=9 || f->fail_alloc || bytes>sizeof f->buf[0]) return 0;
    for (unsigned i=0;i<2;++i) if (!(f->active&(1u<<i))) {
        f->active|=1u<<i;
        *b=(struct bb_vector_block_v541){f->buf[i],bytes,va557(i)};
        return 1;
    }
    return 0;
}
static int release557(void *v,uint64_t owner,uint64_t va) {
    struct fixture557 *f=v;
    ++f->frees;
    for (unsigned i=0;i<2;++i) if (owner==9 && va==va557(i) && (f->active&(1u<<i))) {
        if (f->fail_release && i==0) return 0;
        f->active^=1u<<i;
        return 1;
    }
    return 0;
}
static int key557(void *v,uint64_t cls,unsigned slot,uint64_t *word) {
    struct fixture557 *f=v;
    if (slot!=f->calls%4 || cls<1) return 0;
    ++f->calls;
    if (f->fail_key==slot+1) return 0;
    static const uint64_t words[]={7,UINT64_MAX,0,7};
    *word=words[slot];
    return 1;
}
static size_t grow557(void *v,size_t cap,size_t need) {
    (void)v;
    const size_t next=cap+cap/2;
    return next<need?need:next;
}
static int secondary557(void) {
    struct fixture557 f={0};
    unsigned char h[40]={0},before[40],snapshot[512*16];
    bb_arena_store_v527(h+32,9);
    const uint64_t hva=UINT64_C(0x100010000);
    for (uint64_t cls=1;cls<=128;++cls) {
        const struct bb_vector_block_v541 old={f.buf[0],sizeof f.buf[0],va557(0)};
        if (bb_secondary_insert_v557(h,sizeof h,hva,&old,cls,&f,key557,grow557,
                alloc557,release557)!=BB_SEC_OK) return 1;
    }
    if (f.allocs!=1 || f.frees || f.active!=1 || f.calls!=512 ||
        bb_vector_word_v541(h+16)!=va557(0)+sizeof snapshot) return 2;
    memcpy(before,h,sizeof h); memcpy(snapshot,f.buf[0],sizeof snapshot);
    const struct bb_vector_block_v541 old={f.buf[0],sizeof f.buf[0],va557(0)};
    for (unsigned mode=0;mode<3;++mode) {
        f.calls=0; f.fail_key=mode==0?3u:0u;
        f.fail_alloc=(mode==1); f.fail_release=(mode==2);
        if (bb_secondary_insert_v557(h,sizeof h,hva,&old,129,&f,key557,grow557,
                alloc557,release557)!=BB_SEC_STOP || memcmp(before,h,sizeof h) ||
                memcmp(snapshot,f.buf[0],sizeof snapshot) || f.active!=1) return 3;
    }
    f.calls=0; f.fail_release=0;
    if (bb_secondary_insert_v557(h,sizeof h,hva,&old,129,&f,key557,grow557,
            alloc557,release557)!=BB_SEC_OK || f.active!=2 || f.calls!=4 ||
            bb_vector_word_v541(h+8)!=va557(1) ||
            bb_vector_word_v541(h+16)!=va557(1)+516*16 ||
            bb_vector_word_v541(h+24)!=va557(1)+768*16) return 4;
    unsigned counts[130][3]={{0}};
    for (size_t i=0;i<516;++i) {
        const unsigned char *p=f.buf[1]+16*i;
        const uint64_t k=bb_vector_word_v541(p),cls=bb_vector_word_v541(p+8);
        if (!cls || cls>129 || (k!=0 && k!=7 && k!=UINT64_MAX) ||
                (i && bb_class_key_v556(f.buf[1],i-1)>bb_class_key_v556(f.buf[1],i))) return 5;
        ++counts[cls][k==UINT64_MAX?0u:(k==0?1u:2u)];
    }
    for (unsigned cls=1;cls<=129;++cls)
        if (counts[cls][0]!=1 || counts[cls][1]!=1 || counts[cls][2]!=2) return 6;
    h[16]|=1u; f.calls=0;
    if (bb_secondary_insert_v557(h,sizeof h,hva,NULL,130,&f,key557,grow557,
            alloc557,release557)!=BB_SEC_INVALID || f.calls) return 7;
    return 0;
}

int main(void) {
    const int sec=secondary557();
    if (sec) return 10+sec;
    static const size_t ns[]={32,33,41,42,513};
    static const uint64_t sums[][2]={
        {UINT64_C(0xd603853c438d7e52),UINT64_C(0xd603853c438d7e52)},
        {UINT64_C(0x15e1c2856fd9fba7),UINT64_C(0x1822dd4d417a495)},
        {UINT64_C(0x41e5851b21143013),UINT64_C(0x6cadf8fc21a711e9)},
        {UINT64_C(0x843e886ea1b8b51b),UINT64_C(0x1c4a08a6d762de79)},
        {UINT64_C(0xb2b25d7e1dec1f73),UINT64_C(0x2a501f73c2b0d9b3)},
    };
    unsigned char b[513*16+2];
    unsigned char *p=b+1;
    if (!bb_class_sort_v556(NULL,0,0) || bb_class_sort_v556(p,15,1) ||
        bb_class_sort_v556(NULL,16,1) || bb_class_sort_v556(p,sizeof b-2,514)) return 1;
    for (size_t j=0;j<sizeof ns/sizeof *ns;++j) for (unsigned k=0;k<2;++k) {
        const size_t n=ns[j];
        b[0]=0xc3; p[16*n]=0xa5;
        for (size_t i=0;i<n;++i) {
            bb_arena_store_v527(p+16*i,(uint64_t)((int)((17*i)%11)-5));
            bb_arena_store_v527(p+16*i+8,i+1);
        }
        if (k) {
            if (!bb_class_sort_v556(p,16*n,n)) return 2;
        } else bb_class_sort_rows_v556(p,n,0);
        uint64_t h=0;
        for (size_t i=0;i<n;++i) {
            if (i && bb_class_key_v556(p,i-1)>bb_class_key_v556(p,i)) return 3;
            h=131*h+bb_vector_word_v541(p+16*i+8);
        }
        if (h!=sums[j][k] || b[0]!=0xc3 || p[16*n]!=0xa5) return 4;
    }
    return 0;
}
