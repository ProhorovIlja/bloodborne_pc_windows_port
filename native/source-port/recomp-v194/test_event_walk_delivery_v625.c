/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_walk_delivery_v625.c"
#include <assert.h>

static unsigned char frame[0x590], root[0x160], other[16];
static unsigned step;
static void put(unsigned char *p,void *v) { memcpy(p,&v,sizeof v); }
static int cleanup(void *ctx,void *self,void *const *target) {
    assert(!ctx && self==root && step++==0 && *target==other);
    assert(read_ref620(other)==0x40010000 && frame[0x45b]==0x22);
    write_ref620(other,0x40008000);
    return -1;
}
static void last(void *ctx,void *p) {
    assert(!ctx && p==other && step++==1 && read_ref620(other)==0x7fff8000);
}
int main(void) {
    const BbEventRecord621 r={1,bb_event_body_v621(173),-8};
    const BbEventWalk615 w={NULL,cleanup,NULL};
    put(frame+0x588,root+8); put(frame+0x200,other);
    void *external=other; put(frame+0x128,&external);
    frame[0x458]=2; frame[0x45a]=3; frame[0x45b]=0xa2;
    write_ref620(root,0x8000); write615(root+0x15c,1); write_ref620(other,0x40000000);
    assert(bb_event_walk_delivery_v625(frame,sizeof frame,&r,4,&w,last,NULL)==-1);
    assert(!step && frame[0x45b]==0xa2 && read_ref620(other)==0x40000000);
    frame[0x45a]=2;
    assert(bb_event_walk_delivery_v625(frame,sizeof frame,&r,4,&w,last,NULL)==-2);
    assert(step==2 && read_ref620(other)==0x7fff0000);
    return 0;
}
