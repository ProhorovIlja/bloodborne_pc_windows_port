/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_PROVIDER_PUBLISH_V658_H
#define BB_PROVIDER_PUBLISH_V658_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Shared-mutex and guard setup are upstream. Caller serializes publication
 * and keeps the cell, object and bindings live, aligned and disjoint. */
struct bb_provider_cache_v658 { uintptr_t published; };
struct bb_provider_calls_v658 {
    void *ctx;
    uintptr_t (*get_dependency)(void *);
    int (*query)(void *, uintptr_t, uint32_t *);
};

static inline uintptr_t bb_provider_publish_v658(struct bb_provider_cache_v658 *cell,
        unsigned char *obj, size_t size, uintptr_t table,
        const struct bb_provider_calls_v658 *calls) {
    if (!cell) return 0;
    if (cell->published) return cell->published;
    if (!obj || ((uintptr_t)obj & 7) || size < 0x50 || sizeof(uintptr_t) != 8 ||
        !table || !calls || !calls->get_dependency || !calls->query) return 0;
    const uintptr_t dependency = calls->get_dependency(calls->ctx);
    uint32_t flags = 0;
    if (!dependency || !calls->query(calls->ctx,dependency,&flags) || !(flags & 0x20)) return 0;
    /* The retail success path leaves +0x18 and bytes past +0x50 untouched.
     * The transient base table before querying is not exposed in this ABI. */
    const uintptr_t zero = 0;
    memcpy(obj, &table, 8);
    memcpy(obj+8, &zero, 8);
    memcpy(obj+16, &zero, 8);
    memset(obj+0x20, 0, 0x30);
    memcpy(obj+0x38, &dependency, 8);
    cell->published = (uintptr_t)obj;
    return cell->published;
}
#endif
