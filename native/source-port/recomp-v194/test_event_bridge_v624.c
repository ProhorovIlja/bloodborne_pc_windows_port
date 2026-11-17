/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_bridge_v624.c"
#include <assert.h>

static unsigned char frame[0x590], object[0x38];
static int item, payload;
static unsigned calls;
static void put624(unsigned char *p,void *v) { memcpy(p,&v,8); }
static void indexed624(void *p,void *arg,size_t n) {
    assert(p==&item && arg==&payload && n==1 && frame[0x45b]==0x33);
    ++calls;
}
static BbEventIndexed614 index_route624(void *p) { assert(p==&item); return indexed624; }
static void forward624(void *p,void *arg) {
    assert(p==object && (uintptr_t)arg==UINT32_MAX && frame[0x45b]==0x33);
    ++calls;
}
static BbEventForward614 forward_route624(void *p) { assert(p==object); return forward624; }
int main(void) {
    const BbBridgeOps624 ops={NULL,index_route624,forward_route624};
    BbEventRecord621 r={1,bb_event_body_v621(98),-8};
    put624(frame+0x588,object+8);
    object[0xc]=1; frame[0x45b]=0xb3;
    assert(bb_event_bridge_v624(98,frame,sizeof frame,&r,&ops)==0 && frame[0x45b]==0x33);
    void *rows[]={&item};
    put624(object+0x20,rows); put624(object+0x28,rows+1);
    put624(frame+0x200,&payload);
    r.body=bb_event_body_v621(125); frame[0x45b]=0xb3;
    assert(bb_event_bridge_v624(125,frame,sizeof frame,&r,&ops)==1 && calls==1);
    frame[0x208]=1;
    assert(bb_event_bridge_v624(125,frame,sizeof frame,&r,&ops)==0 && calls==1);
    uint32_t external=UINT32_MAX;
    frame[0x45a]=1; frame[0x45b]=0xb3; put624(frame+0x118,&external);
    r.body=bb_event_body_v621(157);
    assert(bb_event_bridge_v624(157,frame,sizeof frame,&r,&ops)==1 && calls==2);
    frame[0x45b]=0xb3;
    assert(bb_event_bridge_v624(98,frame,sizeof frame,&r,&ops)==-1 && frame[0x45b]==0xb3);
    assert(bb_event_bridge_v624(173,frame,sizeof frame,&r,&ops)==-1 && calls==2);
    return 0;
}
