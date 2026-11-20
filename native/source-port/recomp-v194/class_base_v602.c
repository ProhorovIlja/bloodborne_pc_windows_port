/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_base_v598.c"

/* The short retail getter calls an out-of-line version of the same
 * descriptor initializer. Keep one native implementation. A failed
 * prepare or allocation is not equivalent to a successful null parent. */
int bb_class_base_v602(BbClass90State597 *base,void **allocator,
                       const BbClass90Ops597 *op,unsigned char **out) {
    if (!out) return -1;
    *out=bb_class_base_v598(base,allocator,op);
    return *out?0:-1;
}
