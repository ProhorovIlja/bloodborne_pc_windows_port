/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_PROFILE_V695_H
#define BB_RESUME_PROFILE_V695_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

static inline uint64_t bb_profile_get695(const unsigned char *p, size_t off) {
    uint64_t v;
    memcpy(&v,p+off,8);
    return v;
}
static inline void bb_profile_put695(unsigned char *p, size_t off, uint64_t v) {
    memcpy(p+off,&v,8);
}

/* Spans must be disjoint and refer to the objects already resolved by the
 * caller. tag is the dword 16 bytes before the pointer at vector+0x50.
 * now is an injected counter in the same clock domain as the saved counter.
 * This executes accounting only, not the subsequent stack guard or RET. */
static inline int bb_profile_exit695(unsigned char *vm, size_t vm_size,
        const unsigned char *vector, size_t vector_size,
        unsigned char *profile, size_t profile_size, const uint32_t *tag,
        uint64_t now) {
    if (!vm || !vector || !profile || vm_size < 0x50 ||
        vector_size < 0x58 || profile_size < 0x520) return 0;
    uint32_t count = (uint32_t)((bb_profile_get695(vector,0x28) -
                               bb_profile_get695(vector,0x18)) >> 3);
    count *= UINT32_C(0xaaaaaaab);
    int positive = count && !(count & UINT32_C(0x80000000));
    if (positive && !tag) return 0;
    uint64_t elapsed = now - bb_profile_get695(profile,0x510);
    uint64_t saved = bb_profile_get695(profile,0x518);
    uint64_t nested = bb_profile_get695(profile,0x4c8) - saved;
    bb_profile_put695(vm,0x40,0);
    bb_profile_put695(profile,0x510,0);
    bb_profile_put695(profile,0x518,0);
    if (positive && (*tag & 15u) == 9u)
        bb_profile_put695(profile,0x4c0,bb_profile_get695(profile,0x4c0)+nested-elapsed);
    bb_profile_put695(profile,0x4c8,saved);
    bb_profile_put695(profile,0x4d0,bb_profile_get695(profile,0x4d0)+elapsed-nested);
    bb_profile_put695(profile,0x4d8,bb_profile_get695(profile,0x4d8)+nested);
    return 1;
}
#endif
