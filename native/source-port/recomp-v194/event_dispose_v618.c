/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_queue_v617.c"

typedef struct {
    void *ctx,*allocator;
    void (*destroy_payload)(void *,void *);
    void (*free_storage)(void *,void *);
    void (*release_self)(void *,void *);
} BbPacketLifetime618;

/* Serialized. Allocator and all typed host routes must outlive the queue.
 * Cleanup does not free the packet itself; the queue adapter does that. */
void bb_event_destroy_v618(BbQueuePacket617 *p,const BbPacketLifetime618 *op) {
    if (p->payload) {
        void *payload=p->payload,*allocator=op->allocator;
        op->destroy_payload(op->ctx,payload);
        op->free_storage(allocator,payload);
    }
    p->payload=NULL;
    unsigned char *self=p->self;
    if (self) {
        uint32_t word;
        const uint32_t mask=UINT32_C(0x3fff8000);
        memcpy(&word,self+8,4);
        uint32_t next=(word-UINT32_C(0x8000))&mask;
        const uint32_t result=(word&~mask)|(next?next:mask);
        memcpy(self+8,&result,4);
        if (!next) op->release_self(op->ctx,self);
        p->self=NULL;
    }
}

void bb_event_dispose_v618(void *ctx,BbQueuePacket617 *p) {
    const BbPacketLifetime618 *op=ctx;
    void *allocator=op->allocator;
    bb_event_destroy_v618(p,op);
    op->free_storage(allocator,p);
}
