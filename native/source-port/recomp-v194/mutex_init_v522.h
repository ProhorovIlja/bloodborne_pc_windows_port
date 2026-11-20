/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_MUTEX_INIT_V522_H
#define BB_MUTEX_INIT_V522_H
#include <stdint.h>
#include <stddef.h>

enum bb_mutex_op_v522 { BB_ATTR_INIT_V522, BB_ATTR_TYPE_V522, BB_MUTEX_INIT_V522, BB_ATTR_DESTROY_V522 };
typedef int (*bb_mutex_hook_v522)(void *, enum bb_mutex_op_v522, uint64_t,
                                 uint64_t *, uint32_t, uint32_t *);
/* Trusted hooks implement the guest ABI. Attribute storage is host-local and
 * lives only for this call. Hook failure means stop, not retry or fallback.
 * On normal return classify the guest result; do not swallow diagnostics. */
enum bb_mutex_status_v522 { BB_MUTEX_MISS_V522, BB_MUTEX_RETURN_V522, BB_MUTEX_DIAG_V522 };
struct bb_mutex_result_v522 { enum bb_mutex_status_v522 status; uint32_t value, line; };
static inline struct bb_mutex_result_v522 bb_mutex_init_v522(
        uint64_t object, bb_mutex_hook_v522 hook, void *ctx) {
    uint64_t attr=0;
    uint32_t rc=0, ignored=0;
    if (!object || !hook || !hook(ctx,BB_ATTR_INIT_V522,0,&attr,0,&ignored) ||
        !hook(ctx,BB_ATTR_TYPE_V522,0,&attr,2,&ignored) ||
        !hook(ctx,BB_MUTEX_INIT_V522,object,&attr,0,&rc) ||
        !hook(ctx,BB_ATTR_DESTROY_V522,0,&attr,0,&ignored))
        return (struct bb_mutex_result_v522){BB_MUTEX_MISS_V522,0,0};
    if (!rc) return (struct bb_mutex_result_v522){BB_MUTEX_RETURN_V522,0,0};
    if (rc==UINT32_C(0x8002000c) || rc==UINT32_C(0x80020023))
        return (struct bb_mutex_result_v522){BB_MUTEX_RETURN_V522,UINT32_MAX,0};
    return (struct bb_mutex_result_v522){BB_MUTEX_DIAG_V522,rc,rc==UINT32_C(0x80020016)?57u:59u};
}
#endif
