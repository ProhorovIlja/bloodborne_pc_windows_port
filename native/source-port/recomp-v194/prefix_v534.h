/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_PREFIX_V534_H
#define BB_PREFIX_V534_H
#include "ctor_v519.h"

struct bb_leaf_v534 { size_t guard, dst; uint64_t value; };
/* The caller supplies one validated descriptor for each ordered leaf. Never
 * skip an invalid slot or retry after partial writes. No guest code is read. */
static inline size_t bb_leaves_v534(unsigned char *rw, size_t size, uint64_t bias,
        const struct bb_leaf_v534 *leaves, size_t count) {
    size_t i=0;
    if (!leaves) return 0;
    for (;i<count;++i) {
        const struct bb_leaf_v534 *r=leaves+i;
        if (!bb_ctor_v519(rw,size,r->guard,r->dst,r->value,bias)) break;
    }
    return i;
}
#endif
