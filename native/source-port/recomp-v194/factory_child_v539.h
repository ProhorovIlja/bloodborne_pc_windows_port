/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_FACTORY_CHILD_V539_H
#define BB_FACTORY_CHILD_V539_H
#include "factory_seed_v538.h"

enum bb_child_v539 { BB_CHILD_MISS, BB_CHILD_WARM, BB_CHILD_READY, BB_CHILD_REJECTED, BB_CHILD_STOP };
struct bb_child_result_v539 { enum bb_child_v539 status; uint32_t guest_result; };
/* Track host readiness independently from the retail flag. Callers may
 * reproduce returning diagnostics, but must not use the lock on error. */
static inline struct bb_child_result_v539 bb_child_init_v539(unsigned char *p,
        size_t n, uint64_t va, void *ctx,
        int (*init)(void *,uint64_t,uint32_t *), int (*diagnostic)(void *,unsigned)) {
    uint32_t rc=0;
    if (!p || n<17 || !va || va>UINT64_MAX-16 || !init || !diagnostic)
        return (struct bb_child_result_v539){BB_CHILD_MISS,0};
    if (p[16]) return (struct bb_child_result_v539){BB_CHILD_WARM,0};
    if (!init(ctx,va+8,&rc)) return (struct bb_child_result_v539){BB_CHILD_MISS,0};
    if (rc==UINT32_C(0x8002000c) || rc==UINT32_C(0x80020023))
        return (struct bb_child_result_v539){BB_CHILD_REJECTED,UINT32_MAX};
    unsigned line;
    switch (rc) {
    case UINT32_C(0x80020001): line=77; break;
    case UINT32_C(0x80020010): line=79; break;
    case UINT32_C(0x80020016): line=81; break;
    case UINT32_C(0x8002000e): line=83; break;
    default: line=85; break;
    }
    for (;line<=83;line+=2) if (!diagnostic(ctx,line))
        return (struct bb_child_result_v539){BB_CHILD_STOP,0};
    p[16]=1;
    return (struct bb_child_result_v539){rc?BB_CHILD_REJECTED:BB_CHILD_READY,0};
}
#endif
