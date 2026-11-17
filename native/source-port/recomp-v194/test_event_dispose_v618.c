/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_dispose_v618.c"
#include <assert.h>
#include <stdlib.h>

typedef struct { unsigned seq; BbQueuePacket617 *packet; void *payload; } Trace;
static void destroy(void *v,void *p) {
    Trace *t=v; assert(t->seq++==0 && p==t->payload && p==t->packet->payload);
}
static void drop(void *v,void *p) {
    Trace *t=v;
    if (p==t->payload) assert(t->seq++==1);
    else assert(t->seq++==3 && p==t->packet && !t->packet->self && !t->packet->payload);
}
static void last(void *v,void *p) {
    Trace *t=v; uint32_t word;
    memcpy(&word,(unsigned char *)p+8,4);
    assert(t->seq++==2 && p==t->packet->self && !t->packet->payload && word==0xbfff9234);
}
static BbQueuePacket617 **alloc(void *v,size_t n,size_t a) { (void)v; assert(a==8); return malloc(n); }
static void release(void *v,BbQueuePacket617 **p) { (void)v; free(p); }
int main(void) {
    uint32_t self[3]={0,0,0x80009234};
    unsigned char event[9]={[8]=0x10};
    int payload=1;
    BbQueuePacket617 keep={self,event,NULL}, incoming={self,event,&payload};
    Trace t={0,&incoming,&payload};
    BbPacketLifetime618 life={&t,&t,destroy,drop,last};
    BbQueueOps617 op={alloc,release,bb_event_dispose_v618,&life};
    BbQueueLane617 lane={.allocator=&t};
    assert(bb_event_enqueue_v617(&lane,&keep,&op)==1);
    assert(bb_event_enqueue_v617(&lane,&incoming,&op)==1);
    assert(t.seq==4 && lane.end-lane.begin==1 && *lane.begin==&keep);
    free(lane.begin);
    return 0;
}
