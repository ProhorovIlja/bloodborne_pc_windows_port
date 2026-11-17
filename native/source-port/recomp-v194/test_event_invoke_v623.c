/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_invoke_v623.c"
#include <assert.h>

static unsigned char frame[0x590], object[48];
static unsigned calls;
static void call98(void *p) { assert(p==object+16 && frame[0x45b]==0x33); ++calls; }
static void call125(void *p,void *arg,uint32_t n) {
    assert(arg==object && n==UINT32_MAX); call98(p);
}
static void call157(void *p,uint32_t n) { assert(n==UINT32_MAX); call98(p); }
static BbErasedInvoke623 resolve(void *p,size_t offset) {
    assert(p==object+16 && frame[0x45b]==0xb3 && offset==24);
    return (BbErasedInvoke623)call157;
}
int main(void) {
    void *p=object+24; memcpy(frame+0x588,&p,8);
    p=object; memcpy(frame+0x200,&p,8);
    memset(frame+0x208,0xff,4);
    memset(frame+0x210,0xff,4);
    const BbInvokeRoute623 routes[]={
        {(BbErasedInvoke623)call98,-8,0,NULL},
        {(BbErasedInvoke623)call125,-8,0,NULL},
        {NULL,-8,24,resolve}};
    const unsigned ids[]={98,125,157};
    for (unsigned i=0;i<3;++i) {
        frame[0x45b]=0xb3;
        assert(bb_event_invoke_v623(ids[i],frame,sizeof frame,routes+i)==1);
    }
    frame[0x45b]=0xb3; frame[0x45a]=1;
    assert(bb_event_invoke_v623(125,frame,sizeof frame,routes+1)==-1);
    assert(bb_event_invoke_v623(173,frame,sizeof frame,routes)==-1);
    assert(bb_event_invoke_v623(98,frame,0x58f,routes)==-1);
    assert(calls==3 && frame[0x45b]==0xb3);
    return 0;
}
