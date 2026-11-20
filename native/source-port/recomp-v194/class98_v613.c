/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class90_v597.c"
#include "yaw_pitch_v607.c"

typedef struct {
    uintptr_t table;
    int (*invoke)(unsigned char *,void (*)(void *));
    intptr_t adjustment;
} BbEventBinding613;
_Static_assert(sizeof(BbEventBinding613)==24 && offsetof(BbEventBinding613,invoke)==8 &&
    offsetof(BbEventBinding613,adjustment)==16,"event binding ABI");

/* Serialized startup; binding must outlive all registrations. The bind
 * callback returns 1 on success. A failed call is terminal for this startup. */
int bb_class98_v613(BbClass90State597 *s,const BbClass90Ops597 *o,
    int (*base)(void *,unsigned char **),BbEventBinding613 *binding,uintptr_t table,
    const char *name,const uint16_t *wide,
    int (*bind)(void *,unsigned char *,const BbEventBinding613 *,const char *,const uint16_t *)) {
    if (!binding || !table || !name || !wide || !bind) return -1;
    int rc=bb_class90_checked_v603(s,o,base);
    if (rc) return rc;
    *binding=(BbEventBinding613){table,bb_yaw_pitch_v607,0};
    return bind(o->ctx,s->published,binding,name,wide)==1?0:-7;
}
