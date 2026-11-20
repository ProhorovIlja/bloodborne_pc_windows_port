/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_base_v598.c"
#include <assert.h>
#include <stdio.h>
typedef struct {
    BbClass90State597 child,base;
    BbClass90Ops597 base_op;
    unsigned prep,alloc,kind,insert,diag,mode;
} Test;
static int prepare(void *p) { Test *t=p; ++t->prep; return t->mode==1; }
static void *allocate(void *p) { Test *t=p; ++t->alloc; return t->mode==2?NULL:p; }
static unsigned kind(void *p,void *a) { Test *t=p; assert(a==p); ++t->kind; return t->mode==3?0:0x73; }
static int insert(void *p,unsigned char *d) {
    Test *t=p; assert(d==t->child.descriptor && !t->base.published); ++t->insert; return 0;
}
static unsigned char *get(void *p) { Test *t=p; return bb_class_base_v598(&t->base,&t->child.allocator,&t->base_op); }
static void diagnostic(void *p,unsigned n) { Test *t=p; assert(n==0x3e); ++t->diag; }
static uintptr_t word(const void *p) { uintptr_t v; memcpy(&v,p,8); return v; }
int main(void) {
    Test t={0};
    BbClass90Ops597 child={&t,1,2,3,4,prepare,allocate,kind,insert,get,diagnostic};
    t.base_op=child; t.base_op.class_table=5;
    memset(t.base.descriptor,0xa5,sizeof t.base.descriptor);
    assert(bb_class90_v597(&t.child,&child)==0);
    assert(t.prep==2 && t.alloc==1 && t.kind==2 && t.insert==1 && !t.diag);
    unsigned char *d=t.base.descriptor;
    assert(t.base.published==d && parent597(t.child.published)==d);
    assert(word(d)==5 && !word(d+8) && !word(d+0x10) && d[0x18]==0xa5);
    assert(word(d+0x38)==(uintptr_t)&t && !word(d+0x40) && !word(d+0x48));
    for (unsigned i=0;i<128;++i) assert(get(&t)==d);
    assert(t.prep==2 && t.alloc==1 && t.kind==2);
    for (unsigned m=1;m<=3;++m) {
        t.base=(BbClass90State597){0}; t.child.allocator=NULL;
        t.prep=t.alloc=t.kind=t.diag=0; t.mode=m;
        assert(!get(&t) && !t.base.published);
        assert(t.prep==1 && t.alloc==(m>=2) && t.kind==(m==3) && t.diag==(m==3));
    }
    puts("V598: #90 -> real native base getter, one shared allocator, warm and failure paths OK");
}
