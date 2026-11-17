/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class98_v613.c"
#include "event_dispatch_v614.c"
#include "event_walk_v615.c"

typedef void (*BbErasedEvent621)(void);
typedef struct {
    uintptr_t table;
    BbErasedEvent621 body;
    intptr_t adjustment;
} BbEventRecord621;
_Static_assert(sizeof(BbEventRecord621)==24 && offsetof(BbEventRecord621,body)==8 &&
    offsetof(BbEventRecord621,adjustment)==16,"event record ABI");

/* Only erase a pointer for storage; restore its original type before calling.
 * These host adapters have different signatures; no generic PS4 ABI call. */
BbErasedEvent621 bb_event_body_v621(unsigned ctor) {
    switch (ctor) {
    case 98: return (BbErasedEvent621)bb_yaw_pitch_v607;
    case 125: return (BbErasedEvent621)bb_event_indexed_v614;
    case 157: return (BbErasedEvent621)bb_event_forward_v614;
    case 173: return (BbErasedEvent621)bb_event_walk_v615;
    default: return NULL;
    }
}

/* Serialized startup. Keep the record live for as long as the class registry.
 * bind must return 1 on success. Errors are terminal, not retryable. */
int bb_class_event_v621(BbClass90State597 *state,const BbClass90Ops597 *op,
    int (*base)(void *,unsigned char **),BbEventRecord621 *record,uintptr_t table,
    const char *name,const uint16_t *wide,
    int (*bind)(void *,unsigned char *,const BbEventRecord621 *,const char *,const uint16_t *),
    unsigned ctor) {
    BbErasedEvent621 body=bb_event_body_v621(ctor);
    if (!body || !record || !table || !name || !wide || !bind) return -1;
    int rc=bb_class90_checked_v603(state,op,base);
    if (rc) return rc;
    *record=(BbEventRecord621){table,body,0};
    return bind(op->ctx,state->published,record,name,wide)==1?0:-7;
}
