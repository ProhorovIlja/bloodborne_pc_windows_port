/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_walk_v615.c"
#include "event_close_queue_v619.c"
#include <assert.h>
#include <stdlib.h>

typedef struct {
    BbCloseQueue619 route;
    BbEventQueue619 queue;
    BbCloseOps616 close;
    BbMemberClass608 cls;
    unsigned char node[0x160], tokens[2][12];
    void *owner[5], *target;
    unsigned mode, phase, allocations, reserves, drops, destroyed;
} Fixture;
static void before(void *v,unsigned char *self) {
    Fixture *f=v; assert(self==f->node && f->phase++==0);
}
static const BbMemberClass608 *get(void *v,unsigned char *self) {
    Fixture *f=v; assert(self==f->node); return &f->cls;
}
static void dispatch(void *v,void *q,unsigned char *s,const void *ev,void *m) {
    Fixture *f=v; assert(f->phase>0 && f->phase<3);
    assert(q==&f->queue && s==f->node && ev==f->tokens[f->phase-1] && !m);
    ++f->phase;
}
static void *allocate(void *v,size_t n,size_t a) {
    Fixture *f=v; assert(a==8 && f->phase==3 && n==(f->allocations?8:24));
    return ++f->allocations==f->mode?NULL:malloc(n);
}
static BbQueuePacket617 **reserve(void *v,size_t n,size_t a) {
    Fixture *f=v; assert(a==8 && n==8); ++f->reserves;
    return f->mode==3?NULL:malloc(n);
}
static void release(void *v,BbQueuePacket617 **p) { (void)v; free(p); }
static void destroy(void *v,void *p) { Fixture *f=v; assert(*(uintptr_t *)p==42); ++f->destroyed; }
static void drop(void *v,void *p) { ++((Fixture *)v)->drops; free(p); }
static void last(void *v,void *p) { (void)v; (void)p; abort(); }
static int enqueue(void *v,void *q,BbClosePacket616 *p) {
    Fixture *f=v; assert(f->phase++==3); return bb_close_enqueue_v619(&f->route,q,p);
}
static int cleanup(void *v,void *s,void *const *target) {
    Fixture *f=v; assert(target==&f->target); return bb_event_close_v616(s,&f->close)<0;
}
int main(void) {
    for (unsigned mode=0;mode<5;++mode) for (unsigned lane=0;lane<2;++lane) {
        Fixture f={.mode=mode};
        f.route=(BbCloseQueue619){{&f,&f,destroy,drop,last},reserve,release};
        f.queue.active=mode==4?2:lane;
        f.queue.lane[lane].allocator=&f;
        f.owner[4]=&f.queue; void *own=f.owner; memcpy(f.node+0x20,&own,8);
        f.node[0x6f]=2; write615(f.node+8,0x80009234); write615(f.node+0x15c,1);
        f.close=(BbCloseOps616){&f,before,get,dispatch,allocate,enqueue,{f.tokens[0],f.tokens[1]},42};
        BbEventWalk615 walk={NULL,cleanup,&f};
        int ok=mode==0 || mode==2;
        assert(bb_event_walk_v615(f.node,&f.target,1,&walk)==(ok?2:-2));
        assert(f.phase==4 && f.node[0x6f]==(ok?1:2));
        assert(!f.queue.lane[1-lane].begin);
        assert(f.reserves==(ok || mode==3));
        if (ok) {
            assert(f.queue.lane[lane].end-f.queue.lane[lane].begin==1);
            BbQueuePacket617 *p=*f.queue.lane[lane].begin;
            assert(p->self==f.node && p->event==f.tokens[0] && (!!p->payload)==(mode==0));
            assert(!f.drops && read615(f.node+8)==0x80011234);
            bb_event_dispose_v618(&f.route.lifetime,p);
            free(f.queue.lane[lane].begin);
        } else assert(!f.queue.lane[lane].begin);
        assert(read615(f.node+8)==0x80009234);
        assert(f.drops==(mode==1?0:mode==2?1:2));
        assert(f.destroyed==(mode!=1 && mode!=2));
    }
    return 0;
}
