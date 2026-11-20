/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_sort_v556.h"

#include "class_secondary_v557.h"
#include "class_table_v554.h"
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
static int secondary557(void) {
    struct fixture557 f={0};
    unsigned char h[40]={0},before[40],snapshot[512*16];
    bb_arena_store_v527(h+32,9);
    const uint64_t hva=UINT64_C(0x100010000);
    for (uint64_t cls=1;cls<=128;++cls) {
        const struct bb_vector_block_v541 old={f.buf[0],sizeof f.buf[0],va557(0)};
        if (bb_secondary_insert_v557(h,sizeof h,hva,&old,cls,&f,key557,
                alloc557,release557)!=BB_SEC_OK) return 1;
    }
    if (f.allocs!=1 || f.frees || f.active!=1 || f.calls!=512 ||
        bb_vector_word_v541(h+16)!=va557(0)+sizeof snapshot) return 2;
    memcpy(before,h,sizeof h); memcpy(snapshot,f.buf[0],sizeof snapshot);
    const struct bb_vector_block_v541 old={f.buf[0],sizeof f.buf[0],va557(0)};
    for (unsigned mode=0;mode<3;++mode) {
        f.calls=0; f.fail_key=mode==0?3u:0u;
        f.fail_alloc=(mode==1); f.fail_release=(mode==2);
        if (bb_secondary_insert_v557(h,sizeof h,hva,&old,129,&f,key557,
                alloc557,release557)!=BB_SEC_STOP || memcmp(before,h,sizeof h) ||
                memcmp(snapshot,f.buf[0],sizeof snapshot) || f.active!=1) return 3;
    }
    f.calls=0; f.fail_release=0;
    if (bb_secondary_insert_v557(h,sizeof h,hva,&old,129,&f,key557,
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
    if (bb_secondary_insert_v557(h,sizeof h,hva,NULL,130,&f,key557,
            alloc557,release557)!=BB_SEC_INVALID || f.calls) return 7;
    return 0;
}

/* Synthetic seam: run both table helpers on the same class IDs.
 * This does not assert retail call order or atomicity between tables. */
static int tables557(void) {
    struct fixture557 f={0};
    unsigned char primary[40]={0}, secondary[40]={0}, rows[64]={0};
    const uint64_t hp=UINT64_C(0x100010000), hs=hp+64, vp=hp+128;
    const struct bb_vector_block_v541 pb={rows,sizeof rows,vp};
    bb_arena_store_v527(primary+8,vp); bb_arena_store_v527(primary+16,vp+32);
    bb_arena_store_v527(primary+24,vp+64); bb_arena_store_v527(primary+32,5);
    bb_arena_store_v527(secondary+32,9);
    bb_arena_store_v527(rows,1); bb_arena_store_v527(rows+24,7);
    const uint64_t row[4]={2,3,4,7};
    if (bb_class_insert_v554(primary,sizeof primary,hp,&pb,row,&f,
            alloc557,release557)!=BB_CLASS_OK || f.allocs || f.frees ||
            bb_vector_word_v541(rows)!=1 || bb_vector_word_v541(rows+32)!=2 ||
            bb_vector_word_v541(primary+16)!=vp+64) return 1;
    const struct bb_vector_block_v541 old={f.buf[0],sizeof f.buf[0],va557(0)};
    for (uint64_t cls=1;cls<=2;++cls)
        if (bb_secondary_insert_v557(secondary,sizeof secondary,hs,&old,cls,&f,key557,
                alloc557,release557)!=BB_SEC_OK) return 2;
    static const uint64_t keys[]={UINT64_MAX,UINT64_MAX,0,0,7,7,7,7};
    static const uint64_t classes[]={1,2,1,2,1,1,2,2};
    for (size_t i=0;i<8;++i)
        if (bb_vector_word_v541(f.buf[0]+16*i)!=keys[i] ||
            bb_vector_word_v541(f.buf[0]+16*i+8)!=classes[i]) return 3;
    return f.calls!=8 || f.allocs!=1 || f.frees ||
        bb_vector_word_v541(primary+16)!=vp+64 || bb_vector_word_v541(rows+32)!=2;
}

/* The original grows on the first append past capacity, not before the
 * batch. The allocator sees two new rows when starting at 510 / 512. */
struct boundary559 {
    struct fixture557 f;
    unsigned char *header;
    unsigned alloc_after, key_before_reserve;
};
static int key559(void *v,uint64_t cls,unsigned slot,uint64_t *word) {
    struct boundary559 *b=v;
    if (!b->f.allocs) ++b->key_before_reserve;
    return key557(&b->f,cls,slot,word);
}
static int alloc559(void *v,uint64_t owner,size_t bytes,struct bb_vector_block_v541 *out) {
    struct boundary559 *b=v;
    b->alloc_after=(unsigned)((bb_vector_word_v541(b->header+16)-
        bb_vector_word_v541(b->header+8))/16);
    return alloc557(&b->f,owner,bytes,out);
}
static int release559(void *v,uint64_t owner,uint64_t va) {
    struct boundary559 *b=v;
    return release557(&b->f,owner,va);
}
static int boundary559(void) {
    unsigned char h[40]={0};
    struct boundary559 b={0};
    b.header=h;
    const uint64_t hva=UINT64_C(0x100010000), va=va557(0);
    bb_arena_store_v527(h+32,9);
    if (bb_secondary_insert_v557(h,sizeof h,hva,NULL,1,&b,key559,alloc559,release559)!=BB_SEC_OK ||
            b.key_before_reserve || b.alloc_after || b.f.allocs!=1) return 1;
    const struct bb_vector_block_v541 old={b.f.buf[0],sizeof b.f.buf[0],va};
    bb_arena_store_v527(h+16,va+510*16);
    b.f.fail_alloc=1;
    if (bb_secondary_insert_v557(h,sizeof h,hva,&old,2,&b,key559,alloc559,release559)!=BB_SEC_STOP ||
            b.alloc_after!=512 || b.f.calls!=8 || b.f.active!=1 || b.f.frees ||
            bb_vector_word_v541(h+16)!=va+512*16 ||
            bb_vector_word_v541(b.f.buf[0]+510*16+8)!=2 ||
            bb_vector_word_v541(b.f.buf[0]+511*16+8)!=2) return 2;
    return 0;
}

/* End-to-end secondary table oracle for synthetic input, taken after the
 * original append/grow/sort returned. Only output checksums are stored.
 * The test normalizes the appended class pointer to the synthetic ID 129. */
static int oracle560(void) {
    static const struct { size_t cap, used; uint64_t sum; } cases[] = {
        {0,0,UINT64_C(0xfffff6d7701591fb)}, {32,28,UINT64_C(0xd0755aaf7d25a5b7)},
        {33,29,UINT64_C(0xfc13bc9514bef616)}, {38,37,UINT64_C(0xabeeae725fbf9d96)},
        {41,38,UINT64_C(0xdfa7c6bee448a871)}, {512,508,UINT64_C(0x5b4921fc4d7dd747)},
        {512,509,UINT64_C(0xa648ec3cfcdb2186)}, {512,510,UINT64_C(0xca78986d2a683531)},
        {512,511,UINT64_C(0xe06b0fa88cbf4308)}, {512,512,UINT64_C(0xb62864c8f66b951b)},
    };
    for (size_t c=0;c<sizeof cases/sizeof *cases;++c) {
        const size_t cap=cases[c].cap, n=cases[c].used;
        struct fixture557 f={0};
        unsigned char h[40]={0};
        const uint64_t va=va557(0);
        const struct bb_vector_block_v541 old={f.buf[0],sizeof f.buf[0],va};
        bb_arena_store_v527(h+32,9);
        if (cap) {
            f.active=1;
            bb_arena_store_v527(h+8,va);
            bb_arena_store_v527(h+16,va+16*n);
            bb_arena_store_v527(h+24,va+16*cap);
        }
        for (size_t i=0;i<n;++i) {
            bb_arena_store_v527(f.buf[0]+16*i,(uint64_t)((int)((i*97)%24)-3));
            bb_arena_store_v527(f.buf[0]+16*i+8,0x4200+i);
        }
        if (bb_secondary_insert_v557(h,sizeof h,UINT64_C(0x100010000),cap?&old:NULL,
                129,&f,key557,alloc557,release557)!=BB_SEC_OK ||
                (f.active!=1 && f.active!=2) || f.calls!=4) return 1;
        const unsigned slot=f.active==2;
        if (bb_vector_word_v541(h+8)!=va557(slot) ||
                bb_vector_word_v541(h+16)!=va557(slot)+16*(n+4)) return 2;
        uint64_t sum=0;
        for (size_t i=0;i<2*(n+4);++i) sum=sum*131+bb_vector_word_v541(f.buf[slot]+8*i);
        if (sum!=cases[c].sum) return 3;
    }
    return 0;
}

int main(void) {
    if (bb_secondary_slots_v559(0)!=1 || bb_secondary_slots_v559(1)!=2 ||
            bb_secondary_slots_v559(511)!=766 || bb_secondary_slots_v559(512)!=768 ||
            bb_secondary_slots_v559(768)!=1152 || bb_secondary_slots_v559(SIZE_MAX/16)) return 29;
    const int both=tables557();
    if (both) return 20+both;
    const int sec=secondary557();
    if (sec) return 10+sec;
    const int edge=boundary559();
    if (edge) return 30+edge;
    const int oracle=oracle560();
    if (oracle) return 40+oracle;
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
