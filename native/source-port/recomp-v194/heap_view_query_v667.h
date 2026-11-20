/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_HEAP_VIEW_QUERY_V667_H
#define BB_HEAP_VIEW_QUERY_V667_H
#include <stdint.h>

/* x86-64 hidden result pointer precedes the interface and mode.
 * The attested leaf does not read either of those explicit arguments. */
static inline uint32_t *bb_heap_view_flags_v667(uint32_t *out, const void *view, uint32_t mode) {
    (void)view;
    (void)mode;
    *out=UINT32_C(0x73);
    return out;
}
#endif
