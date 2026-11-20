/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct BbEventType626 {
    uintptr_t tag;
    const struct BbEventType626 *base;
} BbEventType626;
typedef struct { intptr_t key; const BbEventType626 *type; } BbEventTypeRow626;
typedef struct { intptr_t probe, identity; } BbEventTypeKey626;
typedef struct {
    const BbEventTypeRow626 *rows; /* sorted by signed key, first equal wins */
    size_t count, depth;
    BbEventTypeKey626 key[2];       /* per delivery entry, not constructor-wide */
    int (*receiver)(void *,const void *,const BbEventType626 *);
    void *ctx;
} BbEventValidation626;
_Static_assert(sizeof(BbEventTypeRow626)==16 && offsetof(BbEventType626,base)==8,"type ABI");
static const void *pointer626(const unsigned char *p) {
    const void *out; memcpy(&out,p,sizeof out); return out;
}
static const BbEventType626 *expected626(const BbEventValidation626 *op,BbEventTypeKey626 key) {
    size_t lo=0,hi=op->count;
    while (lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if (op->rows[mid].key<key.probe) lo=mid+1;
        else hi=mid;
    }
    return lo<op->count && op->rows[lo].key==key.identity?op->rows[lo].type:NULL;
}
/* Does not mutate the frame. All host pointers must describe live storage.
 * The receiver route owns the high-bit check (including any platform effects).
 * Reject excessive ancestry and missing routes rather than fall back. */
int bb_event_validate_v626(unsigned ctor,const unsigned char *frame,size_t size,
                           const BbEventValidation626 *op) {
    unsigned n;
    switch (ctor) {
    case 98: n=0; break;
    case 125: case 157: n=1; break;
    case 173: n=2; break;
    default: return -1;
    }
    if (!frame || size<0x590 || frame[0x458]!=n) return 0;
    unsigned flags=frame[0x45a];
    for (unsigned i=0;i<n;++i) {
        if (!(flags&(1u<<i))) continue;
        if (!pointer626(frame+0x118+i*16)) return 0;
        if (!op || !op->depth || (op->count && !op->rows)) return -1;
        const BbEventType626 *want=expected626(op,op->key[i]);
        const BbEventType626 *have=pointer626(frame+0x110+i*16);
        if (!want) return 0;
        size_t depth=op->depth;
        for (;have && have!=want && depth;--depth) have=have->base;
        if (!have) return 0;
        if (have!=want) return -1;
    }
    const void *self=pointer626(frame+0x588);
    if (!self) return 0; /* also reject unchecked null host objects */
    if (!(frame[0x45b]&0x80)) return 1;
    if (!op || !op->receiver) return -1;
    int rc=op->receiver(op->ctx,self,pointer626(frame+0x580));
    return rc==1?1:rc==0?0:-1;
}

/* Gate an already selected typed host delivery route. A negative body result
 * can follow effects and must not be retried as if no invocation occurred. */
int bb_event_deliver_v626(unsigned ctor,unsigned char *frame,size_t size,
    const BbEventValidation626 *validation,
    int (*body)(void *,unsigned,unsigned char *,size_t),void *ctx) {
    if (!body) return -1;
    int rc=bb_event_validate_v626(ctor,frame,size,validation);
    if (rc!=1) return rc;
    rc=body(ctx,ctor,frame,size);
    return rc<0?rc:1;
}
