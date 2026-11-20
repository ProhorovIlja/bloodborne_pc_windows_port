/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_GUARDED_PUBLISH_V569_H
#define BB_GUARDED_PUBLISH_V569_H
#include <stddef.h>
#include <stdint.h>

/* Single-threaded startup only. target is an already resolved address point,
 * not an RVA into the original executable. Caller owns its relocation and
 * lifetime. The original tests only the low byte but writes a full qword. */
static inline int bb_guarded_publish_v569(unsigned char *data,size_t n,
    size_t dst,size_t guard,uint64_t target) {
    if (!data || n<8 || dst>n-8 || guard>n-8 || (dst|guard)&7 ||
        guard<=dst || guard-dst!=8 || !target) return 0;
    if (!data[guard]) {
        for (unsigned i=0;i<8;++i)
            data[dst+i]=(unsigned char)(target>>(8*i));
        data[guard]=1;
        for (unsigned i=1;i<8;++i) data[guard+i]=0;
    }
    return 1;
}
#endif
