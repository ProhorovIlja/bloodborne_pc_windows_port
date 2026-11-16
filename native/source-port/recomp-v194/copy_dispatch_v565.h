/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_COPY_DISPATCH_V565_H
#define BB_COPY_DISPATCH_V565_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Trusted, immutable tables generated offline from a verified dump.
 * Entries must be sorted by unique RVA; table storage must not alias data.
 * Dispatch preserves the order of writes. It never loads or calls guest code.
 * This is a memory-only adapter for void startup calls, not a CPU ABI shim. */
struct bb_copy_entry_v565 { uint64_t rva; size_t first, count; };
struct bb_copy_write_v565 { uint64_t dst; size_t constant; };
enum bb_copy_result_v565 { BB_COPY_INVALID, BB_COPY_MISS, BB_COPY_OK };
static inline enum bb_copy_result_v565 bb_copy_dispatch_v565(
    const struct bb_copy_entry_v565 *entries, size_t ne,
    const struct bb_copy_write_v565 *writes, size_t nw,
    const unsigned char *constants, size_t nc,
    uint64_t rva, unsigned char *data, uint64_t base, size_t size) {
    if (ne && !entries) return BB_COPY_INVALID;
    size_t lo=0, hi=ne;
    while (lo<hi) {
        size_t m=lo+(hi-lo)/2;
        if (entries[m].rva<rva) lo=m+1; else hi=m;
    }
    if (lo==ne || entries[lo].rva!=rva) return BB_COPY_MISS;
    const size_t first=entries[lo].first, n=entries[lo].count;
    if (!data || !writes || !constants || size<16 || nc>SIZE_MAX/16 ||
        size>UINT64_MAX-base || !n || first>nw || n>nw-first) return BB_COPY_INVALID;
    for (size_t i=0; i<n; ++i) {
        const struct bb_copy_write_v565 w=writes[first+i];
        if ((w.dst&15) || w.dst<base || w.dst-base>size-16 || w.constant>=nc)
            return BB_COPY_INVALID;
    }
    for (size_t i=0; i<n; ++i) {
        const struct bb_copy_write_v565 w=writes[first+i];
        memcpy(data+(size_t)(w.dst-base),constants+16*w.constant,16);
    }
    return BB_COPY_OK;
}
#endif
