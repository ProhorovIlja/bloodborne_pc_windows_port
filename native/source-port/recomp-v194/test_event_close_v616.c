/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_walk_v615.c"
#include "event_close_v616.c"
#include <assert.h>

typedef struct {
    unsigned char self[0x160];
    void *owners[3][5],*target;
    BbMemberClass608 child,parent;
    BbMemberRow608 rows[2];
    BbCloseOps616 close;
    BbClosePacket616 packet;
    uintptr_t payload;
    unsigned step,allocs,fail;
} Fixture;
static void owner(Fixture *f,unsigned i) {
    void *p=f->owners[i]; memcpy(f->self+0x20,&p,sizeof p);
}
static void pre(void *ctx,unsigned char *self) {
    Fixture *f=ctx; assert(f->step++==0 && self==f->self); owner(f,0);
}
static const BbMemberClass608 *get(void *ctx,unsigned char *self) {
    Fixture *f=ctx; assert((f->step==1 || f->step==3) && self==f->self);
    owner(f,++f->step/2); return &f->child;
}
static void send(void *ctx,void *queue,unsigned char *self,const void *event,void *member) {
    Fixture *f=ctx; unsigned i=(f->step-2)/2;
    assert((f->step==2 || f->step==4) && self==f->self && queue==f->owners[i][4]);
    assert(event==f->close.event[i] && member==f->rows[i].member); ++f->step;
}
static void *alloc(void *ctx,size_t n,size_t align) {
    Fixture *f=ctx; assert(f->step==5 && align==8 && n==(f->allocs?8:24));
    if (++f->allocs==f->fail) return NULL;
    return f->allocs==1?(void *)&f->packet:&f->payload;
}
static int enqueue(void *ctx,void *queue,BbClosePacket616 *p) {
    Fixture *f=ctx; assert(f->step++==5 && queue==f->owners[2][4] && f->self[0x6f]==2);
    if (f->fail==1) assert(!p);
    else {
        assert(p==&f->packet && p->self==f->self && p->event==f->close.event[0]);
        assert(p->payload==(f->fail==2?NULL:&f->payload));
        if (p->payload) assert(f->payload==42);
    }
    return f->fail==3;
}
static int close_walk(void *ctx,void *self,void *const *target) {
    Fixture *f=ctx; assert(target==&f->target);
    return bb_event_close_v616(self,&f->close)<0;
}
int main(void) {
    for (unsigned fail=0;fail<4;++fail) {
        Fixture f={.fail=fail};
        f.rows[0]=(BbMemberRow608){&f.child,"_OnPreClose",NULL,11};
        f.rows[1]=(BbMemberRow608){NULL,"_OnPostClose",NULL,12};
        f.child.parent=&f.parent; f.parent.begin=f.rows; f.parent.end=f.rows+2;
        for (unsigned i=0;i<3;++i) f.owners[i][4]=f.owners+i;
        f.close=(BbCloseOps616){&f,pre,get,send,alloc,enqueue,{&f.child,&f.parent},42};
        f.self[0x6f]=2;
        write615(f.self+8,UINT32_C(0xbfff8123)); write615(f.self+0x15c,1);
        const BbEventWalk615 walk={NULL,close_walk,&f};
        assert(bb_event_walk_v615(f.self,&f.target,1,&walk)==(fail==3?-2:2));
        assert(f.step==6 && f.allocs==(fail==1?1:2));
        assert(f.self[0x6f]==(fail==3?2:1));
        assert(read615(f.self+8)==(fail==1?UINT32_C(0xbfff8123):UINT32_C(0x80000123)));
        if (fail!=3) assert(!bb_event_close_v616(f.self,NULL) && f.step==6);
    }
    return 0;
}
