/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_event_v621.c"
#include "event_invoke_v623.c"
#include "event_dispatch_v620.c"

/* Called after retail type/receiver validation. Object and external slots
 * must be live. Only the native #173 record is callable through this route. */
int bb_event_walk_delivery_v625(unsigned char *frame,size_t size,
    const BbEventRecord621 *record,size_t budget,const BbEventWalk615 *walk,
    void (*last)(void *,void *),void *ctx) {
    if (!frame || size<0x590 || frame[0x458]!=2 || !record || !record->table ||
        record->body!=bb_event_body_v621(173) || !walk || !last || !budget) return -1;
    BbInvokeArgs623 a;
    if (decode623(98,frame,size,record->adjustment,&a)<0) return -1;
    void *arg[2];
    for (unsigned i=0;i<2;++i) {
        const unsigned char *slot=frame+0x200+0x28*i;
        if (frame[0x45a]&(1u<<i)) {
            slot=ptr623(frame+0x118+0x10*i);
            if (!slot) return -1;
        }
        arg[i]=ptr623(slot);
    }
    frame[0x45b]&=0x7f;
    retain620(arg[0]); retain620(arg[1]);
    int rc=bb_event_walk_v615(a.receiver,&arg[0],budget,walk);
    const BbDispatchOps620 refs={.last=last,.ctx=ctx};
    drop620(arg[1],&refs); drop620(arg[0],&refs);
    return rc;
}
