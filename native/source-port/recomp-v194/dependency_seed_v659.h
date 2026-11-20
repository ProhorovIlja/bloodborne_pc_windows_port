/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_DEPENDENCY_SEED_V659_H
#define BB_DEPENDENCY_SEED_V659_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { BB_DEPENDENCY_BYTES_V659 = 0x490, BB_DEPENDENCY_VIEW_V659 = 0x458 };
struct bb_dependency_tables_v659 { uintptr_t primary_lock, view, secondary_lock; };

/* Initial object layout only. The caller still owns lock initialization,
 * the 1 MiB backing store and the later activation path. Do not publish
 * a live provider dependency based solely on this function's success. */
static inline int bb_dependency_seed_v659(unsigned char *p, size_t n,
        struct bb_dependency_tables_v659 t) {
    if (!p || ((uintptr_t)p & 7) || n < BB_DEPENDENCY_BYTES_V659 ||
        sizeof(uintptr_t) != 8 || !t.primary_lock || !t.view || !t.secondary_lock)
        return 0;
    const uintptr_t self = (uintptr_t)p, zero = 0;
    memset(p, 0, 0x440);
    memcpy(p+0x440, &t.primary_lock, 8);
    p[0x450] = 0;
    memcpy(p+0x458, &t.view, 8);
    memcpy(p+0x460, &self, 8);
    memcpy(p+0x468, &zero, 8);
    memcpy(p+0x470, &t.secondary_lock, 8);
    p[0x480] = 0;
    memset(p+0x488, 0, 4);
    return 1;
}
#endif
