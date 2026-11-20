/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_HEAP_REGISTRY_BOOT_V664_H
#define BB_HEAP_REGISTRY_BOOT_V664_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { BB_BOOT_REGISTRY_HEADER_V664=40, BB_BOOT_REGISTRY_STRIDE_V664=24,
       BB_BOOT_REGISTRY_CAPACITY_V664=32 };
struct bb_boot_registry_ops_v664 {
    void *ctx;
    void *(*allocate)(void *, size_t, size_t);
    int (*release)(void *, void *);
};

/* Cold registry prefix only. Call with a seeded, locked heap before any
 * publication to other threads. The first word of the header and the
 * backing records are untouched until their consumers initialize them. */
static inline int bb_boot_registry_v664(unsigned char *owner, size_t owner_size,
        const struct bb_boot_registry_ops_v664 *ops) {
    if (!owner || owner_size<0x48c || sizeof(uintptr_t)!=8 ||
        !ops || !ops->allocate || !ops->release) return 0;
    uintptr_t current;
    memcpy(&current,owner+0x468,8);
    if (current) return 0;
    const size_t span=BB_BOOT_REGISTRY_STRIDE_V664*BB_BOOT_REGISTRY_CAPACITY_V664;
    unsigned char *header=ops->allocate(ops->ctx,BB_BOOT_REGISTRY_HEADER_V664,8);
    if (!header) return 0;
    unsigned char *records=ops->allocate(ops->ctx,span,16);
    if (!records) return ops->release(ops->ctx,header) ? 0 : -1;
    const uintptr_t start=(uintptr_t)records, end=start+span, parent=(uintptr_t)owner;
    const uintptr_t result=(uintptr_t)header;
    const uint32_t granularity=0x1000;
    memcpy(header+8,&start,8);
    memcpy(header+16,&start,8);
    memcpy(header+24,&end,8);
    memcpy(header+32,&parent,8);
    memcpy(owner+0x488,&granularity,4);
    memcpy(owner+0x468,&result,8);
    return 1;
}
#endif
