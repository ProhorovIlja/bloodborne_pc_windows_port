/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_UNLOCK_V531_H
#define BB_UNLOCK_V531_H
#include <stdint.h>

enum bb_unlock_status_v531 { BB_UNLOCK_MISS, BB_UNLOCK_RETURN, BB_UNLOCK_DIAG };
struct bb_unlock_result_v531 { enum bb_unlock_status_v531 status; uint32_t line; };
/* Stop at the first unresolved diagnostic. In particular, guest EPERM is
 * swallowed by the retail wrapper, but does not prove the lock was released. */
static inline struct bb_unlock_result_v531 bb_unlock_v531(
    uint64_t object, int (*predicate)(void *,uint64_t,uint32_t *),
    int (*unlock)(void *,uint64_t,uint32_t *), void *ctx) {
    uint32_t r;
    if (!object || object>UINT64_MAX-8 || !predicate || !unlock ||
        !predicate(ctx,object,&r)) return (struct bb_unlock_result_v531){BB_UNLOCK_MISS,0};
    if (!(r&255u)) return (struct bb_unlock_result_v531){BB_UNLOCK_DIAG,153};
    if (!unlock(ctx,object+8,&r)) return (struct bb_unlock_result_v531){BB_UNLOCK_MISS,0};
    if (!r || r==UINT32_C(0x80020001)) return (struct bb_unlock_result_v531){BB_UNLOCK_RETURN,0};
    return (struct bb_unlock_result_v531){BB_UNLOCK_DIAG,r==UINT32_C(0x80020016)?192u:197u};
}
#endif
