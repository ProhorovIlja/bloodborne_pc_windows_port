/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_STARTUP_MUTEX_PROBE_V479_H
#define BB_STARTUP_MUTEX_PROBE_V479_H
#include "startup_memory_v478.h"

/* The direct leaf only updates AL. This is not scePthreadMutexLock and
 * does not read or dereference the mutex handle at receiver + 8. */
static inline int bb_mutex_probe_v479(struct bb_memory_v478 *memory,
    uint64_t site, uint64_t expected_site, uint64_t receiver,
    uint64_t expected_receiver, uint64_t *rax) {
    if (!memory || !rax || !site || site != expected_site || !receiver ||
        receiver != expected_receiver || receiver > UINT64_MAX-16) return 0;
    const unsigned char *p=bb_memory_at_v478(&memory->data,receiver+16,1);
    if (!p) return 0;
    *rax=(*rax & ~UINT64_C(255)) | *p;
    return 1;
}
#endif
