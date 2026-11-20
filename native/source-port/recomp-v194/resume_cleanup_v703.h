/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_CLEANUP_V703_H
#define BB_RESUME_CLEANUP_V703_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Resolve the receiver and slot at the time of the call, not at entry
 * to the outer continuation. The opaque argument is not dereferenced. */
typedef int (*bb_invoke703)(void *, unsigned, uint64_t);
static inline int bb_resume_cleanup703(const void *record, size_t bytes,
                                       void *ctx, bb_invoke703 invoke) {
    if (!record || bytes < 0x39) return 0;
    const unsigned char *p = record;
    if (!p[0x38]) return 1;
    uint64_t arg;
    memcpy(&arg, p+0x10, sizeof arg);
    return invoke && invoke(ctx,0x68,arg);
}
#endif
