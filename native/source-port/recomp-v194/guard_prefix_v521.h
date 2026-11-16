/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_GUARD_PREFIX_V521_H
#define BB_GUARD_PREFIX_V521_H
#include <stddef.h>
#include <stdint.h>

enum bb_hook_v521 { BB_ACQUIRE_V521, BB_RELEASE_V521, BB_TEST_V521, BB_INIT_V521 };
typedef int (*bb_call_v521)(void *, enum bb_hook_v521, uint64_t, uint32_t *);

/* A shared startup block, not a guard implementation or a constructor.
 * Hooks use guest addresses and a zero status on a missing target. A failed
 * hook can leave partial effects: the caller must stop, not retry or fallback. */
static inline int bb_guard_prefix_v521(unsigned char *rw, size_t size,
        uint64_t base, size_t guard, size_t done, size_t storage,
        uint64_t vtable, bb_call_v521 call, void *ctx) {
    if (!rw || !call || size<17 || size>UINT64_MAX-base || guard>=size || done>=size ||
        guard==done || storage>size-17 || !vtable) return 0;
    const uint64_t va=base+storage;
    const size_t pad=(size_t)((UINT64_C(0)-va)&7);
    if (pad>size-17-storage) return 0;
    const size_t obj=storage+pad;
    if ((guard>=obj && guard<=obj+16) || (done>=obj && done<=obj+16)) return 0;
    uint32_t r=0;
    if (!rw[guard]) {
        if (!call(ctx,BB_ACQUIRE_V521,base+guard,&r)) return 0;
        if (r) {
            rw[done]=0;
            if (!call(ctx,BB_RELEASE_V521,base+guard,&r)) return 0;
        }
    }
    if (!rw[done]) {
        rw[obj+16]=0;
        for (unsigned i=0;i<8;++i) rw[obj+i]=(unsigned char)(vtable>>(i*8));
        if (!call(ctx,BB_TEST_V521,base+obj,&r)) return 0;
        if (!(r&255)) {
            if (!call(ctx,BB_INIT_V521,base+obj+8,&r)) return 0;
            if (!r) rw[obj+16]=1;
        }
        rw[done]=1;
    }
    return 1;
}
#endif
