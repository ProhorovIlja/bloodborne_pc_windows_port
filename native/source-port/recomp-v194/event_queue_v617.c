/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct { void *self; const void *event; void *payload; } BbQueuePacket617;
typedef struct {
    uint64_t tag;
    BbQueuePacket617 **begin, **end, **limit;
    void *allocator;
} BbQueueLane617;
typedef struct {
    BbQueuePacket617 **(*alloc)(void *,size_t,size_t);
    void (*release)(void *,BbQueuePacket617 **);
    void (*dispose)(void *,BbQueuePacket617 *);
    void *ctx;
} BbQueueOps617;
_Static_assert(sizeof(BbQueueLane617)==40 && sizeof(BbQueuePacket617)==24,"queue ABI");

/* Serialized. A valid accepted or duplicate packet is consumed. Failure
 * leaves ownership with the caller. Slots and event pointers are host data.
 * Unlike the retail OOM path, a null packet or event is rejected explicitly. */
int bb_event_enqueue_v617(BbQueueLane617 *lane,BbQueuePacket617 *packet,
                          const BbQueueOps617 *op) {
    if (!lane || !packet || !packet->event || !op || !op->alloc ||
        !op->release || !op->dispose || !lane->allocator) return -1;
    uintptr_t b=(uintptr_t)lane->begin,e=(uintptr_t)lane->end,l=(uintptr_t)lane->limit;
    if (((b|e|l)&7) || b>e || e>l || (!b && l)) return -1;
    size_t used=(e-b)/8, cap=(l-b)/8;
    unsigned flags=((const unsigned char *)packet->event)[8];
    if (flags&0x30) {
        for (size_t i=0;i<used;++i) {
            BbQueuePacket617 *old=lane->begin[i];
            if (!old || old==packet) return -1;
            if (old->self!=packet->self || old->event!=packet->event) continue;
            if (flags&0x10) { op->dispose(op->ctx,packet); return 1; }
            memmove(lane->begin+i,lane->begin+i+1,(used-i-1)*8);
            --lane->end; --used;
            op->dispose(op->ctx,old);
            break;
        }
    }
    if (used==cap) {
        const size_t max=SIZE_MAX/8;
        if (cap>=max) return 0;
        size_t grown=cap/2<=max-cap?cap+cap/2:cap+1;
        if (grown<=cap) grown=cap+1;
        BbQueuePacket617 **p=op->alloc(lane->allocator,grown*8,8);
        if (!p) return 0;
        if (used) memcpy(p,lane->begin,used*8);
        if (lane->begin) op->release(lane->allocator,lane->begin);
        lane->begin=p; lane->end=p+used; lane->limit=p+grown;
    }
    *lane->end++=packet;
    return 1;
}
