/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "member_lookup_v608.c"
#include <stdint.h>
#include <string.h>

typedef struct {
    void *self;
    const void *event;
    void *payload;
} BbClosePacket616;
typedef struct {
    void *ctx;
    void (*before)(void *,unsigned char *);
    const BbMemberClass608 *(*get_class)(void *,unsigned char *);
    void (*dispatch)(void *,void *queue,unsigned char *self,const void *event,void *member);
    void *(*allocate)(void *,size_t,size_t);
    int (*enqueue)(void *,void *queue,BbClosePacket616 *);
    const void *event[2];
    uintptr_t payload_table;
} BbCloseOps616;
_Static_assert(sizeof(BbClosePacket616)==24,"close packet ABI");
static void *close_ptr616(const unsigned char *p) {
    void *v; memcpy(&v,p,sizeof v); return v;
}
/* Host dispatcher/queue are explicit seams; no guest function addresses.
 * A non-null packet transfers ownership to enqueue, including on failure.
 * Startup is serialized and object/context pointers must be live. */
int bb_event_close_v616(unsigned char *self,const BbCloseOps616 *op) {
    if (!self) return -1;
    if (self[0x6f]<2) return 0;
    if (!op || !op->before || !op->get_class || !op->dispatch || !op->allocate ||
        !op->enqueue || !op->event[0] || !op->event[1] || !op->payload_table) return -1;
    op->before(op->ctx,self);
    static const char *const name[]={"_OnPreClose","_OnPostClose"};
    for (unsigned i=0;i<2;++i) {
        const unsigned char *owner=close_ptr616(self+0x20);
        if (!owner) return -1;
        const BbMemberClass608 *cls=op->get_class(op->ctx,self);
        void *member=NULL;
        if (bb_member_lookup_v608(cls,name[i],256,&member)<0) return -1;
        op->dispatch(op->ctx,close_ptr616(owner+0x20),self,op->event[i],member);
    }
    const unsigned char *owner=close_ptr616(self+0x20);
    if (!owner) return -1;
    BbClosePacket616 *packet=op->allocate(op->ctx,sizeof *packet,8);
    if (packet) {
        uintptr_t *payload=op->allocate(op->ctx,sizeof *payload,8);
        if (payload) *payload=op->payload_table;
        uint32_t word;
        memcpy(&word,self+8,sizeof word);
        word=(word&UINT32_C(0xc0007fff))|((word+UINT32_C(0x8000))&UINT32_C(0x3fff8000));
        memcpy(self+8,&word,sizeof word);
        *packet=(BbClosePacket616){self,op->event[0],payload};
    }
    if (op->enqueue(op->ctx,close_ptr616(owner+0x20),packet)) return -2;
    self[0x6f]=1;
    return 1;
}
