/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_event_v621.c"
#include "event_invoke_v623.c"

typedef struct {
    void (*notify)(void *);
    BbEventIndexed614 (*indexed)(void *);
    BbEventForward614 (*forward)(void *);
} BbBridgeOps624;

/* Delivery after type checks. Only host-owned V621 records are accepted.
 * The receiver and external arguments are live, appropriately sized host
 * objects. Event #173 has different ownership semantics and is not handled. */
int bb_event_bridge_v624(unsigned kind,unsigned char *frame,size_t size,
                        const BbEventRecord621 *record,const BbBridgeOps624 *op) {
    if (!record || !record->table || !op || (kind!=98 && kind!=125 && kind!=157) ||
        record->body!=bb_event_body_v621(kind)) return -1;
    BbInvokeArgs623 a;
    if (decode623(kind,frame,size,record->adjustment,&a)<0) return -1;
    unsigned char *self=a.receiver;
    if (kind==98) {
        frame[0x45b]&=0x7f;
        return bb_yaw_pitch_v607(self,op->notify);
    }
    if (kind==125) {
        uintptr_t b=(uintptr_t)ptr623(self+0x20),e=(uintptr_t)ptr623(self+0x28);
        if ((!b && e) || ((b|e)&7) || e<b) return -1;
        frame[0x45b]&=0x7f;
        return bb_event_indexed_v614((void *const *)b,(e-b)/8,a.argument,a.value,op->indexed);
    }
    BbEventForward614 call=op->forward?op->forward(self):NULL;
    if (!call) return -1;
    frame[0x45b]&=0x7f;
    /* Original mov esi,[...] zero-extends the forwarded register. */
    return bb_event_forward_v614(self,(void *)(uintptr_t)a.value,call);
}
