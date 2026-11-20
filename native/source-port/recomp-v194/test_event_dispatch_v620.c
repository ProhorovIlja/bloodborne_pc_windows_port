/* SPDX-License-Identifier: GPL-2.0-or-later */
#define main v619_regression
#include "test_event_close_queue_v619.c"
#undef main
#include "event_dispatch_v620.c"

typedef struct {
    Fixture f;
    BbDispatchLane620 buckets[31];
    unsigned allocs,frees,fail;
} Integration;
static BbDispatchRow620 *rows620(void *v,size_t n,size_t a) {
    Integration *x=v; assert(a==8 && n%40==0); ++x->allocs;
    return x->fail?NULL:malloc(n);
}
static void free620(void *v,BbDispatchRow620 *p) { ++((Integration *)v)->frees; free(p); }
static void submit620(void *v,void *q,unsigned char *s,const void *ev,void *m) {
    Fixture *f=v;
    Integration *x=(Integration *)f;
    assert(f->phase>0 && f->phase<3 && q==&f->queue && s==f->node);
    assert(ev==f->tokens[f->phase-1]);
    BbDispatchOps620 o={rows620,free620,last,f};
    assert(bb_event_dispatch_v620(x->buckets,s,ev,s,m,0,0,&o)==(m!=NULL));
    ++f->phase;
}
int main(void) {
    assert(!v619_regression());
    Integration x={0}; Fixture *f=&x.f;
    f->route=(BbCloseQueue619){{f,f,destroy,drop,last},reserve,release};
    f->queue.lane[0].allocator=f;
    f->owner[4]=&f->queue; void *own=f->owner; memcpy(f->node+0x20,&own,8);
    f->node[0x6f]=2; write615(f->node+8,0x40009234); write615(f->node+0x15c,1);
    const BbMemberRow608 row={f,"_OnPreClose",NULL,11};
    f->cls.begin=&row; f->cls.end=&row+1;
    f->close=(BbCloseOps616){f,before,get,submit620,allocate,enqueue,{f->tokens[0],f->tokens[1]},42};
    BbDispatchLane620 *bucket=x.buckets+(uintptr_t)f->node%31;
    bucket->allocator=&x;
    const BbEventWalk615 walk={NULL,cleanup,f};
    assert(bb_event_walk_v615(f->node,&f->target,1,&walk)==2);
    assert(f->phase==4 && f->node[0x6f]==1 && x.allocs==1);
    assert(bucket->end-bucket->begin==1 && bucket->begin->event==f->tokens[0]);
    assert(read615(f->node+8)==0x40021234);
    BbQueuePacket617 *p=*f->queue.lane[0].begin;
    assert(p->event==bucket->begin->event && p->self==bucket->begin->source);
    bb_event_dispose_v618(&f->route.lifetime,p);
    const BbDispatchOps620 o={rows620,free620,last,f};
    assert(bb_event_dispatch_v620(x.buckets,f->node,f->tokens[0],f->node,f,19,23,&o)==1);
    assert(x.allocs==1 && bucket->begin->extra==23 && bucket->begin->flags==19);
    x.fail=1;
    assert(bb_event_dispatch_v620(x.buckets,f->node,f->tokens[1],f->node,f,0,0,&o)==-2);
    assert(bucket->end-bucket->begin==1 && !x.frees && read615(f->node+8)==0x40019234);
    clear620(bucket->begin,&o);
    assert(read615(f->node+8)==0x40009234);
    free620(&x,bucket->begin); free(f->queue.lane[0].begin);
    return 0;
}
