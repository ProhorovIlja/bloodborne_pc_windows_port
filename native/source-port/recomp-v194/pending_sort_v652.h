/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_PENDING_SORT_V652_H
#define BB_PENDING_SORT_V652_H
#include "registry_batch_v651.h"

enum { BB_PENDING_SMALL_V652 = 32 };

/* Compare raw 64-bit representations as signed keys without a signed cast.
 * Exact small-array path only. On overflow, do not mutate either registry. */
static inline int bb_pending_less_v652(uint64_t a, uint64_t b) {
    const uint64_t sign = UINT64_C(1) << 63;
    return (a ^ sign) < (b ^ sign);
}

static inline int bb_pending_sort_v652(struct bb_pending_v651 *p, size_t n) {
    if (n > BB_PENDING_SMALL_V652 || (n && !p)) return 0;
    for (size_t i = 1; i < n; ++i) {
        const struct bb_pending_v651 x = p[i];
        size_t j = i;
        while (j && bb_pending_less_v652(x.target, p[j-1].target)) {
            p[j] = p[j-1];
            --j;
        }
        p[j] = x;
    }
    return 1;
}

/* Sorting cannot fail after a successful append: preflight the bound and
 * use the exclusive buffer validated and allocated by V651. */
static inline int bb_registry_register_small_v652(struct bb_registry_v651 *v,
        const struct bb_registry_allocator_v651 *a, struct bb_registry_row_v650 row,
        const uint64_t targets[static 4]) {
    if (!v || v->used > BB_PENDING_SMALL_V652 - 4) return 0;
    if (!bb_registry_register_v651(v,a,row,targets)) return 0;
    return bb_pending_sort_v652(v->pending,v->used);
}
#endif
