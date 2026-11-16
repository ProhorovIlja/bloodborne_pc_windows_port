/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CTOR_LINK_V535_H
#define BB_CTOR_LINK_V535_H
#include <stddef.h>
#include <stdint.h>

enum bb_link_status_v535 { BB_LINK_MISS, BB_LINK_OK, BB_LINK_DIAGNOSTIC, BB_LINK_LIMIT };
/* Shared tail only. Resolve guest values via the caller's data reader.
 * If the original's diagnostic returns, it still writes the head. A
 * missing/nonreturning diagnostic must instead stop without that write. */
static inline enum bb_link_status_v535 bb_ctor_link_v535(uint64_t object,
        uint64_t head, size_t budget, void *ctx,
        int (*read_next)(void *,uint64_t,uint64_t *),
        int (*diagnostic)(void *), int (*write_next)(void *,uint64_t,uint64_t)) {
    if (!object || !read_next || !diagnostic || !write_next) return BB_LINK_MISS;
    for (uint64_t node=head;node;) {
        if (node==object) {
            if (!diagnostic(ctx)) return BB_LINK_DIAGNOSTIC;
            break;
        }
        if (!budget) return BB_LINK_LIMIT;
        --budget;
        if (!read_next(ctx,node,&node)) return BB_LINK_MISS;
    }
    return write_next(ctx,object,head)?BB_LINK_OK:BB_LINK_MISS;
}
#endif
