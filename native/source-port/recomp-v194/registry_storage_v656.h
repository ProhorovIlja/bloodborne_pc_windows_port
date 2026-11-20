/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_REGISTRY_STORAGE_V656_H
#define BB_REGISTRY_STORAGE_V656_H
#include "pending_sort_v653.h"

/* Single stable native backing region, owned by the caller for the lifetime
 * of the registry. Offsets were resolved offline, not supplied by the game.
 * A common base preserves identity and the order of the four address keys.
 * This does not bind the callers that read/write the backing bytes. */
static inline int bb_registry_register_storage_v656(struct bb_registry_v651 *v,
        const struct bb_registry_allocator_v651 *a, struct bb_registry_row_v650 row,
        unsigned char *storage, size_t size, const size_t offsets[static 4]) {
    if (!storage || !size || (uintptr_t)storage > INT64_MAX ||
        size-1 > (uint64_t)INT64_MAX - (uintptr_t)storage) return 0;
    uint64_t keys[4];
    for (size_t i=0;i<4;++i) {
        if (offsets[i]>=size) return 0;
        keys[i]=(uintptr_t)(storage+offsets[i]);
    }
    return bb_registry_register_v653(v,a,row,keys);
}
#endif
