/* SPDX-License-Identifier: GPL-2.0-or-later */
#define main v612_test_main
#include "test_member_register_v612.c"
#undef main
#define bb_yaw_pitch_v607 bb_yaw_pitch_v613_for_test
#define ptr607 ptr613
#define word607 word613
#define radians607 radians613
#include "class98_v613.c"
#undef bb_yaw_pitch_v607
typedef struct {
    Heap heap;
    BbMemberHost612 host;
    unsigned insert,base,bind,fail_base;
} Chain;
static int prep613(void *v) { (void)v; return 0; }
static void *heap613(void *v) { return &((Chain *)v)->heap; }
static unsigned kind613(void *v,void *p) { assert(p==heap613(v)); return 0x73; }
static void diagnose613(void *v,unsigned n) { (void)v; (void)n; abort(); }
static int insert613(void *v,unsigned char *d) {
    Chain *c=v; assert(!parent597(d)); ++c->insert; return 0;
}
static int base613(void *v,unsigned char **out) {
    Chain *c=v; assert(c->insert==1); ++c->base; *out=NULL; return c->fail_base;
}
static int bind613(void *v,unsigned char *d,const BbEventBinding613 *b,const char *n,const uint16_t *w) {
    Chain *c=v; assert(c->base==1 && b->table==3 && !b->adjustment); ++c->bind;
    return bb_member_register_v612(d,n,w,(uintptr_t)b,&c->host);
}
int main(void) {
    assert(v612_test_main()==0);
    for (unsigned f=0;f<3;++f) {
        Chain c={0};
        c.fail_base=f==1; c.heap.fail=f==2?3:0;
        c.host=(BbMemberHost612){&c.heap,&c.heap,1,{alloc612,free612},init612,drop612};
        static const uint16_t wide[]={65,0};
        BbClass90State597 s={0};
        BbClass90Ops597 o={&c,1,2,(uintptr_t)"Example",(uintptr_t)wide,
                           prep613,heap613,kind613,insert613,NULL,diagnose613};
        BbEventBinding613 b={0};
        assert(bb_class98_v613(&s,&o,base613,&b,3,"A",wide,bind613)==(f==1?-6:f==2?-7:0));
        assert(c.insert==1 && c.base==1 && c.bind==(f!=1));
        if (f==1) { assert(!b.table && !c.heap.count); continue; }
        BbMemberRow608 *rows;
        memcpy(&rows,s.descriptor+0x20,sizeof rows);
        assert(rows && rows->member && !strcmp(rows->name,"A"));
        BbMemberObject611 *m=rows->member;
        if (!f) {
            assert(m->handlers.end-m->handlers.begin==1 && *m->handlers.begin==(uintptr_t)&b);
            unsigned char disabled[0x38]={[0xc]=1};
            assert(b.invoke(disabled,NULL)==0);
        } else assert(!m->handlers.begin);
        free(m->handlers.begin); free(m); free(rows);
    }
    return 0;
}
