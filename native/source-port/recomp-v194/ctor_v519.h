/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CTOR_V519_H
#define BB_CTOR_V519_H
#include <stddef.h>
#include <stdint.h>

/* Single-threaded guest startup only. The stored value is a guest address. */
static inline int bb_ctor_v519(unsigned char *rw, size_t n, size_t guard,
        size_t dst, uint64_t value, uint64_t bias) {
    if (!rw || n<8 || guard>n-8 || dst>n-8 ||
        (guard>dst ? guard-dst : dst-guard)<8 || value>UINT64_MAX-bias) return 0;
    if (rw[guard]) return 1;
    value+=bias;
    for (unsigned i=0;i<8;++i) rw[dst+i]=(unsigned char)(value>>(8*i));
    for (unsigned i=0;i<8;++i) rw[guard+i]=(unsigned char)(i==0);
    return 1;
}
#endif
