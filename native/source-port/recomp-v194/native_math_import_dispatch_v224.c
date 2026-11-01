/* SPDX-License-Identifier: GPL-2.0-or-later
 * V224: exact original import offsets -> registered V223 guest math handlers.
 * No original ELF at runtime. Callers must validate writable guest RSP.
 * Not yet connected to the full native RcApi.call dispatch.
 */
#include "native_math_import_dispatch_v224.h"
#include <string.h>
#include <stdint.h>

int shyt_math_import_table_v224_init(ShytMathImportTable *table, uint64_t base,
                                     const ShytMathImportDesc *descs, size_t count) {
    if (!table || !descs || !base || count != 23) return 0;
    ShytMathImportTable candidate;
    memset(&candidate, 0, sizeof(candidate));
    candidate.image_base = base;
    for (size_t i=0; i<count; ++i) {
        if (!descs[i].name || !descs[i].offset ||
            descs[i].offset > UINT64_MAX-base) return 0;
        ShytGuestMathFn fn=shyt_guest_math_v223_find(descs[i].name);
        if (!fn) return 0;
        for (size_t j=0; j<i; ++j)
            if (descs[i].offset==candidate.entries[j].offset ||
                fn==candidate.entries[j].fn) return 0;
        candidate.entries[i].offset=descs[i].offset;
        candidate.entries[i].fn=fn;
    }
    *table=candidate;
    return 1;
}
int shyt_math_import_v224_try_call(const ShytMathImportTable *table,
                                  BbCpu *cpu, uint64_t target, uint64_t next) {
    if (!table || !cpu || !target || !next) return 0;
    ShytGuestMathFn fn=NULL;
    for (size_t i=0;i<23;++i)
        if (table->image_base + table->entries[i].offset == target) {
            fn=table->entries[i].fn;
            break;
        }
    if (!fn || cpu->r[RSP]<8) return 0;
    /* RcApi.call receives an as-yet-unpushed next/return address. */
    cpu->r[RSP]-=8;
    memcpy((void *)(uintptr_t)cpu->r[RSP],&next,8);
    fn(cpu);
    return 1;
}
