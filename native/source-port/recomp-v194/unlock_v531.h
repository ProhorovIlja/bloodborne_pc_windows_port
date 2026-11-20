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
/* A retail return can swallow EPERM. Startup may continue only if the
 * backend actually released the lock. Keep diagnostic parity separate. */
struct bb_unlock_verified_v532 {
    struct bb_unlock_result_v531 retail;
    int released;
};
struct bb_unlock_capture_v532 {
    int (*predicate)(void *,uint64_t,uint32_t *);
    int (*unlock)(void *,uint64_t,uint32_t *);
    void *ctx;
    int released;
};
static inline int bb_unlock_pred_v532(void *x,uint64_t addr,uint32_t *rc) {
    struct bb_unlock_capture_v532 *s=x;
    return s->predicate(s->ctx,addr,rc);
}
static inline int bb_unlock_call_v532(void *x,uint64_t addr,uint32_t *rc) {
    struct bb_unlock_capture_v532 *s=x;
    if (!s->unlock(s->ctx,addr,rc)) return 0;
    s->released=*rc==0;
    return 1;
}
static inline struct bb_unlock_verified_v532 bb_unlock_verify_v532(
        uint64_t object, int (*predicate)(void *,uint64_t,uint32_t *),
        int (*unlock)(void *,uint64_t,uint32_t *), void *ctx) {
    if (!predicate || !unlock)
        return (struct bb_unlock_verified_v532){{BB_UNLOCK_MISS,0},0};
    struct bb_unlock_capture_v532 s={predicate,unlock,ctx,0};
    const struct bb_unlock_result_v531 r=bb_unlock_v531(object,
        bb_unlock_pred_v532,bb_unlock_call_v532,&s);
    return (struct bb_unlock_verified_v532){r,s.released};
}
#endif
