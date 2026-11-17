/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_close_v616.c"
#include "event_dispose_v618.c"

typedef struct {
    unsigned char prefix[0x4d8];
    BbQueueLane617 lane[2];
    uint32_t active;
} BbEventQueue619;
_Static_assert(offsetof(BbEventQueue619,active)==0x528,"queue manager ABI");

typedef struct {
    BbPacketLifetime618 lifetime;
    BbQueuePacket617 **(*reserve)(void *,size_t,size_t);
    void (*release)(void *,BbQueuePacket617 **);
} BbCloseQueue619;

/* V616 transfers a non-null packet even on error. V617 only consumes it on
 * success. Balance its retained object and storage on every rejection.
 * The context and allocator routes must remain live for the queue lifetime. */
int bb_close_enqueue_v619(void *ctx,void *queue,BbClosePacket616 *packet) {
    const BbCloseQueue619 *h=ctx;
    BbEventQueue619 *q=queue;
    if (!packet) return -1;
    const BbQueueOps617 op={h->reserve,h->release,bb_event_dispose_v618,(void *)&h->lifetime};
    if (q && q->active<2 && bb_event_enqueue_v617(&q->lane[q->active],packet,&op)==1)
        return 0;
    bb_event_dispose_v618(op.ctx,packet);
    return -1;
}
