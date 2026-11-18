/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_CASE6_V699_H
#define BB_RESUME_CASE6_V699_H
#include "resume_switch_exit_v698.h"

/* x86 CVTTSD2SI with masked invalid, including its indefinite integer.
 * The port preserves the integer result, not floating-point status flags. */
static inline uint64_t bb_cvtt_v699(double x) {
    if (!(x >= -0x1p63 && x < 0x1p63)) return UINT64_C(0x8000000000000000);
    return (uint64_t)(int64_t)x;
}

/* Use separate binary64 operations; do not compile with fast-math. */
static inline uint64_t bb_case6_ticks_v699(int32_t scale, uint64_t clock) {
    volatile double factor = (double)scale * 0.01;
    volatile double base = (double)(uint32_t)clock + (double)(uint32_t)(clock >> 32) * 0x1p32;
    volatile double x = factor * base;
    if (x >= 0x1p63) return bb_cvtt_v699(x-0x1p63) ^ UINT64_C(0x8000000000000000);
    return bb_cvtt_v699(x);
}

/* record points to the caller-resolved object at vm+0x58. All spans are
 * disjoint. No guest code or object pointers are dispatched by this handler. */
static inline enum bb_profile_result696 bb_case6_exit_v699(
        struct bb_profile_state696 *s, uint32_t value, unsigned char *vm, size_t vs,
        const unsigned char *record, size_t rs,
        const unsigned char *vec, size_t as, unsigned char *profile, size_t ps,
        const uint32_t *tag, uint64_t now, const uint64_t *f, size_t n, uint64_t guard) {
    uint64_t dst;
    uint32_t edi, state, zero = 0;
    int32_t scale;
    if (!s || s->pc != UINT64_C(0xa30b95) || !vm || vs < 0x130 ||
        !record || rs < 0x20 || !f || n < 46) return BB_PROFILE_MISS;
    memcpy(&state,vm+0x60,4);
    if (state != 6 || !bb_zero_switch697(value,vm,vs,&dst,&edi) ||
        dst != UINT64_C(0xa31531)) return BB_PROFILE_MISS;
    memcpy(&scale,vm+0x110,4);
    uint64_t ticks = bb_case6_ticks_v699(scale,bb_profile_get695(record,0x18));
    /* V695 has no callbacks and cannot observe these two fields. Commit
     * them only after its validation, including on the guard-failure arm. */
    if (!bb_profile_exit695(vm,vs,vec,as,profile,ps,tag,now)) return BB_PROFILE_MISS;
    bb_profile_put695(vm,0x128,ticks);
    memcpy(vm+0x60,&zero,4);
    return bb_profile_finish696(s,f,guard,edi);
}
#endif
