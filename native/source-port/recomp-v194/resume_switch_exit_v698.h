/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_SWITCH_EXIT_V698_H
#define BB_RESUME_SWITCH_EXIT_V698_H
#include "resume_profile_return_v696.h"

int bb_zero_switch697(uint32_t, const unsigned char *, size_t, uint64_t *, uint32_t *);

/* Only the default arm is consumed. Other cases leave state unchanged. */
static inline enum bb_profile_result696 bb_zero_exit698(
        struct bb_profile_state696 *s, uint32_t value, unsigned char *vm, size_t vs,
        const unsigned char *vec, size_t as, unsigned char *profile, size_t ps,
        const uint32_t *tag, uint64_t now, const uint64_t *f, size_t n, uint64_t guard) {
    uint64_t target;
    uint32_t edi;
    if (!s || s->pc != UINT64_C(0xa30b95) || !f || n < 46 ||
        !bb_zero_switch697(value,vm,vs,&target,&edi) || target != UINT64_C(0xa31464) ||
        !bb_profile_exit695(vm,vs,vec,as,profile,ps,tag,now)) return BB_PROFILE_MISS;
    return bb_profile_finish696(s,f,guard,edi);
}
#endif
