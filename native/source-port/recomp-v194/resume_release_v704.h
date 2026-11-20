/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_RELEASE_V704_H
#define BB_RESUME_RELEASE_V704_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct bb_release_ops704 {
    void *ctx;
    void (*prepare)(void *, const void *, uint64_t, uint64_t);
    void (*detach)(void *, const void *, uint64_t, uint32_t, uint32_t);
    void (*release)(void *, uint64_t, uint64_t, uint64_t);
};

/* The caller resolves the owner token to a live native span; child tokens
 * are opaque to this function. All non-null slot pointers must be valid
 * through release and may alias each other. The owner span is disjoint. */
static inline int bb_release704(uint64_t *owner, uint64_t *first, uint64_t *second,
        const void *span, size_t bytes, const struct bb_release_ops704 *op) {
    if (!owner || !*owner) return 1;
    if (!span || bytes < 0x3c0 || !op || !op->prepare || !op->detach || !op->release)
        return 0;
    uint64_t self=*owner, a=first ? *first : 0, b=second ? *second : 0, x, y;
    const unsigned char *p=span;
    memcpy(&x,p+0x3b8,8);
    memcpy(&y,p+0x3a8,8);
    op->prepare(op->ctx,span,a,b);
    if (a) {
        op->detach(op->ctx,span,a,0x4000,UINT32_MAX);
        op->release(op->ctx,a,x,y);
        *first=0;
    }
    if (b) {
        op->detach(op->ctx,span,b,0x4000,UINT32_MAX);
        op->release(op->ctx,b,x,y);
        *second=0;
    }
    op->release(op->ctx,self,x,y);
    *owner=0;
    return 1;
}
#endif
