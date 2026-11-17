#include "class90_v597.c"
#include <assert.h>
#include <stdio.h>

typedef struct {
    unsigned calls[6], error;
    unsigned char *base;
    int mode;
} Test;
static int prep(void *p) { Test *t=p; ++t->calls[0]; return t->mode==1; }
static void *alloc(void *p) { Test *t=p; ++t->calls[1]; return t->mode==2?NULL:p; }
static unsigned kind(void *p,void *a) { Test *t=p; assert(a==p); ++t->calls[2]; return t->mode==3?0:0x73; }
static int insert(void *p,unsigned char *d) {
    Test *t=p; uintptr_t a,w;
    memcpy(&a,d+0x40,8); memcpy(&w,d+0x48,8);
    assert(a==3 && w==4); ++t->calls[3]; return t->mode==4;
}
static unsigned char *get(void *p) { Test *t=p; ++t->calls[4]; return t->base; }
static void report(void *p,unsigned n) { Test *t=p; ++t->calls[5]; t->error=n; }
int main(void) {
    Test t={0};
    BbClass90Ops597 op={&t,1,2,3,4,prep,alloc,kind,insert,get,report};
    for (int mode=0;mode<5;++mode) {
        const int status[]={0,-2,-3,-3,-4};
        BbClass90State597 s={0};
        memset(s.descriptor,0xa5,sizeof s.descriptor);
        t=(Test){.mode=mode};
        assert(bb_class90_v597(&s,&op)==status[mode]);
        if (mode) {
            assert(t.calls[0]==1 && t.calls[4]==0);
            if (mode==3) assert(t.error==0x3e && !s.published);
            continue;
        }
        assert(s.published==s.descriptor && !parent597(s.published) && s.descriptor[0x18]==0xa5);
        unsigned char a[16]={0},b[16]={0};
        write597(a+8,(uintptr_t)b); t.base=a;
        assert(!bb_class90_v597(&s,&op) && parent597(s.published)==a);
        assert(t.calls[0]==1 && t.calls[1]==1 && t.calls[2]==1 && t.calls[3]==2 && t.calls[4]==2);
        write597(b+8,(uintptr_t)s.published);
        assert(bb_class90_v597(&s,&op)==-5 && t.error==0x192 && parent597(s.published)==a);
        write597(b+8,(uintptr_t)a);
        assert(bb_class90_v597(&s,&op)==-5 && t.calls[5]==2 && parent597(s.published)==a);
    }
    puts("V597 descriptor shell: cold/warm and failure paths OK");
}
