/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_PURE_VIRTUAL_SLOTS_V634_H
#define BB_PURE_VIRTUAL_SLOTS_V634_H
#include <stddef.h>
#include <stdint.h>

/* Build a typed side table for native dispatch. Input is an offline-normalized
 * list of offsets for one already-resolved import, not an ELF or a live GOT.
 * Publish count only after complete validation. Offsets are opaque lookup keys,
 * never host addresses. Caller serializes construction before worker startup.
 * Input and output must not overlap. */
typedef void (*BbV634Target)(void);
struct bb_v634_reloc { uint64_t offset; uint32_t kind; int64_t addend; };
struct bb_v634_slot { uint64_t offset; BbV634Target target; };
static inline int bb_v634_build(const struct bb_v634_reloc *src, size_t n,
        uint64_t extent, BbV634Target target, struct bb_v634_slot *dst, size_t capacity) {
    if (!src || !dst || !target || !n || n > capacity || extent < 8) return 0;
    for (size_t i=0; i<n; ++i)
        if (src[i].kind != 1 || src[i].addend || src[i].offset % 8 ||
            src[i].offset > extent - 8 || (i && src[i-1].offset >= src[i].offset)) return 0;
    for (size_t i=0; i<n; ++i)
        dst[i] = (struct bb_v634_slot){src[i].offset, target};
    return 1;
}
static inline BbV634Target bb_v634_lookup(const struct bb_v634_slot *slots,
        size_t count, uint64_t offset) {
    if (!slots) return NULL;
    size_t lo=0, hi=count;
    while (lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if (slots[mid].offset < offset) lo=mid+1;
        else hi=mid;
    }
    return lo<count && slots[lo].offset==offset ? slots[lo].target : NULL;
}
#endif
