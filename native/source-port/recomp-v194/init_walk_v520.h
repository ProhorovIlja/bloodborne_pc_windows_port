/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_INIT_WALK_V520_H
#define BB_INIT_WALK_V520_H
#include <stdint.h>
#include <stddef.h>

enum bb_init_status_v520 { BB_INIT_OK_V520, BB_INIT_LAYOUT_V520, BB_INIT_MISS_V520 };
struct bb_init_result_v520 { enum bb_init_status_v520 status; size_t slot, calls; };

/* CUSA03173 profile: the two static forward bounds are the same address.
 * If the loaded bound exceeds it, the original still visits one slot.
 * read returns guest addresses; invoke must reject missing native targets.
 * No restart after a partial run: callbacks may already have side effects. */
static inline struct bb_init_result_v520 bb_init_walk_v520(void *ctx,
        int (*read)(void *, size_t, uint64_t *), int (*invoke)(void *, uint64_t),
        size_t forward, uint64_t forward_va, size_t bound, size_t first, size_t last) {
    struct bb_init_result_v520 r={BB_INIT_LAYOUT_V520,bound,0};
    uint64_t v;
    if (!read || !invoke || first<last || (first-last)%8 || (first-last)/8>=65536 ||
        !read(ctx,bound,&v)) return r;
    if (forward_va<v) {
        r.slot=forward;
        if (!read(ctx,forward,&v) || v==UINT64_MAX) return r;
        if (v) {
            if (!invoke(ctx,v)) { r.status=BB_INIT_MISS_V520; return r; }
            ++r.calls;
        }
    }
    for (size_t slot=first;;slot-=8) {
        r.slot=slot;
        if (!read(ctx,slot,&v)) return r;
        if (v==UINT64_MAX) { r.status=BB_INIT_OK_V520; return r; }
        if (v) {
            if (!invoke(ctx,v)) { r.status=BB_INIT_MISS_V520; return r; }
            ++r.calls;
        }
        if (slot==last) return r;
    }
}
#endif
