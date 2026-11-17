/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLEANUP_V687_H
#define BB_CLEANUP_V687_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef void (*bb_cleanup_call_v687)(void *object);
typedef bb_cleanup_call_v687 (*bb_cleanup_resolve_v687)(void *ctx, uint64_t table, size_t slot);

/* Resolve through the caller's native registry; never dereference a guest
 * table or branch to a guest address. The callback receives the original
 * object before its fields are cleared. */
static inline int bb_cleanup_v687(void *object, size_t size, void *ctx,
                                  bb_cleanup_resolve_v687 resolve) {
    if (!object || size < 0x28) return 0;
    unsigned char *p = object;
    uint64_t table;
    memcpy(&table, p + 8, sizeof(table));
    if (table) {
        if (!resolve) return 0;
        bb_cleanup_call_v687 call = resolve(ctx, table, 0x50);
        if (!call) return 0;
        call(object);
    }
    memset(p + 8, 0, 8);
    memset(p + 0x24, 0, 4);
    return 1;
}
#endif
