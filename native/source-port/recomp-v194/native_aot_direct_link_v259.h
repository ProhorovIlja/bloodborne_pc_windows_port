/* SPDX-License-Identifier: GPL-2.0-or-later
 * V259: native, pre-thread AOT direct-call slot linker.
 * Mirrors pinned original bloodborne-recomp/src/cpu/recomp.c (lines 528-548):
 * bbcpu_recomp_hash must match a function's original code hash BEFORE the
 * direct slot is installed; patched/hooked code stays on the slow route.
 * Does not load PS4 ELF/EBOOT at runtime or blindly enable code.
 */
#ifndef SHYT_NATIVE_AOT_DIRECT_LINK_V259_H
#define SHYT_NATIVE_AOT_DIRECT_LINK_V259_H
#include "native_aot_table_audit_v257.h"
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

/* Trusted owner-provided build-time / mapped-native-code attestation.
 * Return 1 ONLY if the function's bytes match the pinned per-function
 * original image hash and the function was NOT patched or excluded.
 * In a full native port, this requires the owner-built attestation
 * manifest; a caller that always returns 1 breaks the safety contract.
 */
typedef int (*ShytDirectFunctionAttestV259)(
    void *ctx, uint64_t guest_address, uint64_t bytes,
    uint64_t expected_code_hash);

typedef struct {
    size_t direct;
    size_t kept_indirect;
    size_t no_slot;
} ShytDirectStatsV259;

/* Reject duplicate/unaligned generated direct slots before modifying
 * ANY slot. A corrupted table with aliases could otherwise turn calls
 * to one AOT function into calls to a different function. O(n log n)
 * time, O(n) temporary memory, only during single-threaded boot. */
static int shyt_direct_slot_compare_v269(const void *a,const void *b) {
    const uintptr_t aa=*(const uintptr_t *)a;
    const uintptr_t bb=*(const uintptr_t *)b;
    return (aa>bb)-(aa<bb);
}
static inline int shyt_aot_direct_slots_unique_v269(
    const RcFunction *functions,size_t count) {
    if (!functions || !count || count>SIZE_MAX/sizeof(uintptr_t))
        return 0;
    uintptr_t *addresses=(uintptr_t*)malloc(count*sizeof(*addresses));
    if(!addresses) return 0;
    size_t used=0;
    for(size_t i=0;i<count;++i) {
        if(!functions[i].direct) continue;
        const uintptr_t slot=(uintptr_t)functions[i].direct;
        if(!slot || slot%_Alignof(RcFn)!=0) {
            free(addresses);
            return 0;
        }
        addresses[used++]=slot;
    }
    qsort(addresses,used,sizeof(*addresses),shyt_direct_slot_compare_v269);
    int valid=1;
    for(size_t i=1;i<used;++i) {
        if(addresses[i]==addresses[i-1]) { valid=0;break; }
    }
    free(addresses);
    return valid;
}

/* V268: safe explicit revocation, for a host that loses its original-code
 * attestation or is restarting before game workers begin. This is NOT a
 * concurrent hot-unload; no running guest thread may hold these pointers.
 * A valid table is required before writing its module-owned RcFn slots. */
static inline int shyt_aot_revoke_direct_slots_v268(
    const RcFunction *functions, size_t count, uint64_t image_base,
    ShytDirectStatsV259 *stats)
{
    if (!stats || (!shyt_aot_table_valid_v257(functions,count,image_base) ||
         !shyt_aot_direct_slots_unique_v269(functions,count)))
        return 0;
    ShytDirectStatsV259 result={0};
    for(size_t i=0;i<count;++i) {
        if(functions[i].direct) {
            *functions[i].direct=NULL;
            ++result.kept_indirect;
        } else {
            ++result.no_slot;
        }
    }
    *stats=result;
    return 1;
}

/* Call once before starting any game threads with trusted, writable
 * module-owned RcFn slots. The runtime owns their lifetime; do not
 * call after gameplay starts. No allocation or guest executable reader. */
static inline int shyt_aot_activate_direct_slots_v259(
    const RcFunction *functions, size_t count, uint64_t image_base,
    ShytDirectFunctionAttestV259 attest, void *ctx,
    ShytDirectStatsV259 *stats)
{
    if (!attest || !stats ||
        (!shyt_aot_table_valid_v257(functions,count,image_base) ||
         !shyt_aot_direct_slots_unique_v269(functions,count)))
        return 0;
    ShytDirectStatsV259 result={0};
    for (size_t i=0; i<count; ++i) {
        const RcFunction *fn=&functions[i];
        if (!fn->direct) {
            ++result.no_slot;
            continue;
        }
        /* Old direct pointers may refer to a prior native build/epoch.
         * Clear before the attestation callback can fail/return false. */
        *fn->direct=NULL;
        if (attest(ctx,image_base+fn->offset,fn->size,fn->hash)) {
            *fn->direct=fn->fn;
            ++result.direct;
        } else {
            ++result.kept_indirect;
        }
    }
    *stats=result;
    return 1;
}
#endif
