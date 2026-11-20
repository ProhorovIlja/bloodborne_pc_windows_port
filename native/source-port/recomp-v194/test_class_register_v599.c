/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_register_v599.h"
#include "class_base_v598.c"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    unsigned char p[40],s[40];
    struct bb_vector_block_v541 blocks[2];
    BbClass90State597 child,base;
    BbClass90Ops597 base_ops;
    unsigned step, count[2], freed[2], fail;
    int rc;
} Test;
static int field(void *ctx,uint64_t d,unsigned i,uint64_t *v) {
    Test *t=ctx;
    assert(d==(uintptr_t)t->child.descriptor && t->step++==i);
    if (i>=2) {
        assert(t->blocks[1].data && bb_vector_word_v541(t->p+16)>t->blocks[0].va);
        *v=7-i;
    } else *v=bb_vector_word_v541(t->child.descriptor+0x40+8*i);
    return 1;
}
static int alloc(void *ctx,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    Test *t=ctx; assert(owner==1 || owner==2);
    unsigned idx=(unsigned)owner-1;
    assert(t->step==(idx?(t->count[1]?6:2):2));
    if (t->fail==owner) return 0;
    unsigned char *p=calloc(1,n);
    if (!p) return 0;
    if (!t->count[idx]) assert(n==(idx?0x2000u:0x4000u));
    else assert(n==t->blocks[idx].size+t->blocks[idx].size/2);
    ++t->count[idx];
    *b=(struct bb_vector_block_v541){p,n,(uintptr_t)p};
    /* The old allocation is released synchronously before this call returns
     * to the constructor; its address is retained in the vector snapshot. */
    t->blocks[idx]=*b;
    return 1;
}
static int release(void *ctx,uint64_t owner,uint64_t addr) {
    Test *t=ctx; assert(owner==1 || owner==2);
    unsigned idx=(unsigned)owner-1;
    assert(addr && addr!=t->blocks[idx].va);
    ++t->freed[idx]; free((void *)(uintptr_t)addr); return 1;
}
static int prepare(void *p) { (void)p; return 0; }
static void *getalloc(void *p) { return p; }
static unsigned kind(void *p,void *a) { assert(p==a); return 0x73; }
static void diag(void *p,unsigned n) { (void)p; (void)n; abort(); }
static int insert(void *p,unsigned char *d) {
    Test *t=p;
    const struct bb_class_vector_v599 pv={t->p,(uintptr_t)t->p,t->blocks[0]};
    const struct bb_class_vector_v599 sv={t->s,(uintptr_t)t->s,t->blocks[1]};
    const struct bb_class_ops_v599 op={t,field,alloc,release};
    t->step=0;
    t->rc=bb_class_register_v599(&pv,&sv,(uintptr_t)d,&op);
    return t->rc!=BB_REG_OK;
}
static unsigned char *getbase(void *p) {
    Test *t=p;
    return bb_class_base_v598(&t->base,&t->child.allocator,&t->base_ops);
}
int main(void) {
    static const char name[]="GUITextEditorUtil";
    static const uint16_t wide[]={ 'G','U','I',0 };
    for (unsigned f=0;f<3;++f) {
        Test t={.fail=f};
        bb_arena_store_v527(t.p+32,1); bb_arena_store_v527(t.s+32,2);
        BbClass90Ops597 op={&t,1,2,(uintptr_t)name,(uintptr_t)wide,prepare,getalloc,kind,insert,getbase,diag};
        t.base_ops=op;
        int rc=bb_class90_v597(&t.child,&op);
        if (f) {
            assert(rc==-4 && t.rc==(f==1?BB_REG_PRIMARY_STOP:BB_REG_SECONDARY_STOP));
            assert(t.step==2 && !t.base.published && t.count[0]==(f==2) && !t.count[1]);
        } else {
            assert(rc==0 && t.rc==BB_REG_OK && t.step==6);
            assert(parent597(t.child.published)==t.base.published);
            assert(bb_vector_word_v541(t.blocks[0].data+24)==sizeof name-1);
            assert(bb_vector_word_v541(t.blocks[0].data+8)==(uintptr_t)name);
            assert(bb_vector_word_v541(t.blocks[0].data+16)==(uintptr_t)wide);
            for (unsigned i=1;i<513;++i)
                assert(bb_class90_v597(&t.child,&op)==0);
            assert(t.count[0]==2 && t.freed[0]==1);
            assert(t.count[1]>1 && t.freed[1]==t.count[1]-1);
            assert(bb_vector_word_v541(t.p+16)-t.blocks[0].va==513*32);
            assert(bb_vector_word_v541(t.s+16)-t.blocks[1].va==513*64);
            assert(bb_vector_word_v541(t.p+24)-t.blocks[0].va==768*32);
            uint64_t prev=0;
            for (unsigned i=0;i<513*4;++i) {
                unsigned char *row=t.blocks[1].data+16*i;
                uint64_t k=bb_vector_word_v541(row);
                assert(k>=prev && k>=2 && k<=5);
                assert(bb_vector_word_v541(row+8)==(uintptr_t)t.child.published);
                prev=k;
            }
        }
        for (unsigned i=0;i<2;++i) free(t.blocks[i].data);
    }
    puts("V599: constructor/base + both tables, reserve/growth, OOM gates OK");
}
