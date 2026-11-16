/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RO_V477_H
#define BB_RO_V477_H
#include <stddef.h>
#include <stdint.h>
struct bb_ro_row_v476 { uint64_t address; size_t offset, length; };
struct bb_ro_v476 {
    const struct bb_ro_row_v476 *rows;
    const unsigned char *pool;
    size_t count;
};
int bb_ro_bind_v476(struct bb_ro_v476 *, const struct bb_ro_row_v476 *, size_t, const unsigned char *, size_t);
int bb_ro_strlen_v476(const struct bb_ro_v476 *, uint64_t, size_t *);
int bb_ro_offset_v477(const struct bb_ro_v476 *, uint64_t, size_t, size_t *);
int bb_ro_u16len_v477(const struct bb_ro_v476 *, uint64_t, size_t *);
#endif
