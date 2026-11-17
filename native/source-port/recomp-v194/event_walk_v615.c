/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    int (*release)(void *,void *);
    int (*cleanup)(void *,void *,void *const *);
    void *ctx;
} BbEventWalk615;
static uint32_t read615(const unsigned char *p) {
    uint32_t x; memcpy(&x,p,4); return x;
}
static void write615(unsigned char *p,uint32_t x) { memcpy(p,&x,4); }
static int release_if_zero615(unsigned char *node,const BbEventWalk615 *op) {
    const uint32_t mask=UINT32_C(0x3fff8000), old=read615(node+8);
    /* Retail briefly increments the field, then restores it before dispatch. */
    if (!(old&mask)) {
        write615(node+8,old|mask);
        if (!op->release || op->release(op->ctx,node)) return -2;
    }
    return 0;
}

/* Live nodes and target slot, serialized. A callback may change the slot or
 * following link; retain the pre-callback target for the current comparison.
 * Exhausted budget and missing host routes are terminal, not retail fallback. */
int bb_event_walk_v615(unsigned char *self,void *const *target,size_t budget,
                       const BbEventWalk615 *op) {
    if (!self || !target || !budget || !op) return -1;
    const int active=read615(self+0x15c)!=0;
    const void *stop=*target;
    int rc=release_if_zero615(self,op);
    if (rc) return rc;
    if (!active) {
        if (stop==self) write615(self+0x15c,1);
        return 1;
    }
    unsigned char *node=self;
    for (;;) {
        if (stop==node) return 1;
        memcpy(&node,node+0x128,sizeof node);
        if (!node) return op->cleanup && !op->cleanup(op->ctx,self,target)?2:-2;
        if (!--budget) return -1;
        stop=*target;
        rc=release_if_zero615(node,op);
        if (rc) return rc;
    }
}
