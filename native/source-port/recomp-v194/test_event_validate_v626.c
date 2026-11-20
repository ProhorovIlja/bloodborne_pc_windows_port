/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_validate_v626.c"
#ifdef BB_TEST_WALK
#include "event_walk_delivery_v625.c"
#else
#include "event_bridge_v624.c"
#endif
#include <assert.h>

static unsigned char frame[0x590], object[0x160];
static BbEventType626 base={7,NULL}, child={8,&base};
static BbEventRecord621 binding;
static unsigned calls, checks;
static void set626(size_t offset,const void *ptr) { memcpy(frame+offset,&ptr,sizeof ptr); }
static int receiver626(void *ctx,const void *self,const BbEventType626 *type) {
    assert(!ctx && self==object && (frame[0x45b]&0x80));
    ++checks;
    return type==&child;
}
#ifdef BB_TEST_WALK
static void last626(void *ctx,void *p) { (void)ctx; (void)p; assert(0); }
#endif
static int run626(void *ctx,unsigned k,unsigned char *f,size_t n) {
    assert(!ctx && f==frame);
    ++calls;
#ifdef BB_TEST_WALK
    const BbEventWalk615 walk={0};
    assert(k==173);
    return bb_event_walk_delivery_v625(f,n,&binding,1,&walk,last626,NULL);
#else
    const BbBridgeOps624 bridge={0};
    assert(k==98);
    return bb_event_bridge_v624(k,f,n,&binding,&bridge);
#endif
}
int main(void) {
#ifdef BB_TEST_WALK
    const unsigned ctor=173, count=2;
    uint32_t ref=0x8000; memcpy(object+8,&ref,sizeof ref);
#else
    const unsigned ctor=98, count=0;
    object[0xc]=1; /* disabled body still counts as successfully delivered */
#endif
    BbEventType626 cycle={0,&cycle};
    BbEventTypeRow626 rows[]={{-9,NULL},{5,&base},{5,NULL},{7,&child}};
    BbEventValidation626 op={rows,4,2,{{5,5},{6,7}},receiver626,NULL};
    void *external=NULL;
    set626(0x588,object); set626(0x580,&child);
    set626(0x110,&child); set626(0x118,&external);
    set626(0x120,&child); set626(0x128,&external);
    frame[0x458]=2; frame[0x45a]=3;
    assert(bb_event_validate_v626(173,frame,sizeof frame,&op)==1);
    op.key[1].identity=6;
    assert(bb_event_validate_v626(173,frame,sizeof frame,&op)==0);
    op.key[1].identity=7;
    set626(0x110,&cycle); frame[0x45b]=0x80;
    assert(bb_event_validate_v626(173,frame,sizeof frame,&op)==-1 && !checks);
    set626(0x110,&child);
    assert(bb_event_validate_v626(125,frame,sizeof frame,&op)==0 && !checks);
    frame[0x458]=(unsigned char)count;
    binding=(BbEventRecord621){1,bb_event_body_v621(ctor),0};
    set626(0x580,&base);
    assert(bb_event_deliver_v626(ctor,frame,sizeof frame,&op,run626,NULL)==0);
    assert(checks==1 && !calls && frame[0x45b]==0x80);
    set626(0x580,&child);
    assert(bb_event_deliver_v626(ctor,frame,sizeof frame,&op,run626,NULL)==1);
    assert(checks==2 && calls==1 && frame[0x45b]==0);
    return 0;
}
