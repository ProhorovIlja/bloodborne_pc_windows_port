/* SPDX-License-Identifier: GPL-2.0-or-later
 * V257: fail-closed real AOT bbrecomp RcFunction registry validation.
 * This examines an in-memory native C table after bb_recomp_init; it
 * does not parse/load any PS4 EBOOT or ELF at program startup.
 */
#ifndef SHYT_AOT_TABLE_AUDIT_V257_H
#define SHYT_AOT_TABLE_AUDIT_V257_H
#include "recomp/rc.h"
#include <stddef.h>
#include <stdint.h>

static inline int shyt_aot_table_valid_v257(
    const RcFunction *table, size_t count, uint64_t image_base) {
    if (!table || !count || count > 1000000u || !image_base)
        return 0;
    uint64_t previous = 0;
    for (size_t i = 0; i < count; ++i) {
        const RcFunction *fn = &table[i];
        /* Ordering is required by pinned bbrecomp's original table.
         * Overlapping code ranges can be legitimate in an x86 binary,
         * so reject duplicate/unsorted starts, not overlapping ends. */
        if (!fn->fn || !fn->size || (i && fn->offset <= previous) ||
            fn->offset > UINT64_MAX-image_base ||
            fn->size > UINT64_MAX-(image_base+fn->offset))
            return 0;
        previous = fn->offset;
    }
    return 1;
}
#endif
