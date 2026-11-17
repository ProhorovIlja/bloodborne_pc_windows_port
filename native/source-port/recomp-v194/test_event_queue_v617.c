/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_queue_v617.c"
#include <assert.h>
#include <stdlib.h>

typedef struct { int fail; size_t bytes; unsigned frees; BbQueuePacket617 *disposed; } State;
static BbQueuePacket617 **reserve(void *v,size_t n,size_t a) {
    State *s=v; assert(a==8); s->bytes=n; return s->fail?NULL:malloc(n);
}
static void release(void *v,BbQueuePacket617 **p) { ++((State *)v)->frees; free(p); }
static void dispose(void *v,BbQueuePacket617 *p) { ((State *)v)->disposed=p; }
int main(void) {
    State s={0}; BbQueueLane617 lane={.tag=77,.allocator=&s};
    BbQueueOps617 op={reserve,release,dispose,&s};
    unsigned char ev[12]={0},other[12]={0};
    BbQueuePacket617 a={&s,ev,NULL},b={&s,other,NULL},c={&s,ev,&lane};
    assert(bb_event_enqueue_v617(&lane,NULL,&op)==-1 && !lane.begin);
    assert(bb_event_enqueue_v617(&lane,&a,&op)==1 && s.bytes==8);
    s.fail=1;
    assert(bb_event_enqueue_v617(&lane,&b,&op)==0 && *lane.begin==&a && !s.frees);
    s.fail=0;
    assert(bb_event_enqueue_v617(&lane,&b,&op)==1 && s.bytes==16 && s.frees==1);
    ev[8]=0x30;
    assert(bb_event_enqueue_v617(&lane,&c,&op)==1 && s.disposed==&c && lane.begin[0]==&a);
    ev[8]=0x20;
    assert(bb_event_enqueue_v617(&lane,&c,&op)==1 && s.disposed==&a);
    assert(lane.begin[0]==&b && lane.begin[1]==&c && lane.end-lane.begin==2);
    assert(s.bytes==16 && s.frees==1 && lane.tag==77);
    release(&s,lane.begin);
    return 0;
}
