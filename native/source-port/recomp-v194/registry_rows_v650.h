/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_ROWS_V650_H
#define BB_REGISTRY_ROWS_V650_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Native record values supplied by translated callers, not guest pointers.
 * Caller owns a sorted, exclusive buffer; no allocation or registration hooks. */
struct bb_registry_row_v650 { uint64_t object, name, metadata, key; };
_Static_assert(sizeof(struct bb_registry_row_v650) == 32 &&
               offsetof(struct bb_registry_row_v650, key) == 24, "registry layout");

static inline size_t bb_registry_upper_v650(const struct bb_registry_row_v650 *rows,
                                           size_t count, uint64_t key) {
    size_t lo = 0, hi = count;
    while (lo < hi) {
        size_t m = lo + (hi - lo)/2;
        if (key < rows[m].key) hi = m;
        else lo = m + 1;
    }
    return lo;
}

/* Fail closed if growth is required. Equal keys retain insertion order. */
static inline int bb_registry_insert_v650(struct bb_registry_row_v650 *rows,
                                         size_t *count, size_t capacity,
                                         struct bb_registry_row_v650 value) {
    if (!rows || !count || *count >= capacity || capacity > SIZE_MAX / sizeof *rows)
        return 0;
    size_t pos = bb_registry_upper_v650(rows, *count, value.key);
    if (pos < *count)
        memmove(rows + pos + 1, rows + pos, (*count - pos) * sizeof *rows);
    rows[pos] = value;
    ++*count;
    return 1;
}
#endif
