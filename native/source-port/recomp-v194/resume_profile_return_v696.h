/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_PROFILE_RETURN_V696_H
#define BB_RESUME_PROFILE_RETURN_V696_H
#include "resume_profile_v695.h"

struct bb_profile_state696 { uint64_t pc, rax, nv[6]; size_t used; };
enum bb_profile_result696 { BB_PROFILE_MISS, BB_PROFILE_RET, BB_PROFILE_FATAL };

/* Shared native epilogue; caller has validated the frame and state. */
static inline enum bb_profile_result696 bb_profile_finish696(
        struct bb_profile_state696 *s, const uint64_t *f, uint64_t guard, uint32_t edi) {
    if (f[38] != guard) {
        s->pc=UINT64_C(0x2bbe4f8); s->rax=guard; s->used=0;
        return BB_PROFILE_FATAL;
    }
    s->rax=edi; s->pc=f[45]; s->used=46;
    s->nv[0]=f[39]; s->nv[1]=f[44];
    for (size_t i=2;i<6;++i) s->nv[i]=f[38+i];
    return BB_PROFILE_RET;
}

/* Exit arm only: retry and zero-result paths are not consumed. All spans,
 * the frame and state must be disjoint. Register order: BX,BP,R12-R15. */
static inline enum bb_profile_result696 bb_profile_return696(
        struct bb_profile_state696 *s, uint32_t value, unsigned char *vm, size_t vs,
        const unsigned char *vec, size_t as, unsigned char *profile, size_t ps,
        const uint32_t *tag, uint64_t now, const uint64_t *f, size_t n, uint64_t guard) {
    if (!s || s->pc != UINT64_C(0xa30b78) || !value || !f || n < 46 || !vm || vs < 0x50)
        return BB_PROFILE_MISS;
    uint32_t mode;
    memcpy(&mode,vm,4);
    if (mode == UINT32_C(0x80000000) ||
        !bb_profile_exit695(vm,vs,vec,as,profile,ps,tag,now)) return BB_PROFILE_MISS;
    /* Accounting does not touch the first 12 bytes of vm. Commit the
     * V694 write only after the bounds checks in V695 succeed. */
    memcpy(vm+4,vm+8,4);
    return bb_profile_finish696(s,f,guard,0);
}
#endif
