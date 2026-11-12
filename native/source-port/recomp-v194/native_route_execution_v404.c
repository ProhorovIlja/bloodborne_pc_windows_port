/* SPDX-License-Identifier: GPL-2.0-or-later
 * V404: no use of guessed runtime pointers or fallback callbacks.
 * Source-locked 11-function invented-only evidence from V402/V403 CI.
 */
#include "native_route_execution_v404.h"
#include "native_only_approved_v402_generated.h"
#include "native_route_guard_v403_generated.h"
#include <stdlib.h>
#include <string.h>

static int verified_table(const ShytNativeExecutionV404 *route) {
    const RcFunction *f;
    size_t i;
    if (!route || route->bound != 1u || !route->table ||
        !route->owner || route->owner->sealed != 1u ||
        route->owner->released || SHYT_V402_APPROVED_FUNCTION_COUNT !=
        SHYT_V404_SYNTHETIC_FUNCTIONS)
        return 0;
    f = route->table;
    for (i = 0; i < SHYT_V404_SYNTHETIC_FUNCTIONS; ++i) {
        if (f[i].offset != shyt_v402_allowed[i].offset ||
            f[i].size != shyt_v402_allowed[i].size ||
            f[i].hash != shyt_v402_allowed[i].hash ||
            !shyt_v403_is_synthetic_candidate(f[i].offset) ||
            !f[i].fn || !f[i].direct ||
            f[i].fn != route->approved[i] ||
            f[i].direct != route->direct[i] ||
            *f[i].direct != f[i].fn)
            return 0;
    }
    return 1;
}

int shyt_native_execution_bind_v404(ShytNativeExecutionV404 *out,
    ShytNativeOsVmV388 *owner, const RcFunction *compiled, size_t count) {
    ShytNativeExecutionV404 candidate = {0};
    size_t i;
    if (!out || out->bound || !owner || !compiled ||
        owner->sealed != 1u || owner->released ||
        count != SHYT_V404_SYNTHETIC_FUNCTIONS ||
        SHYT_V402_APPROVED_FUNCTION_COUNT != SHYT_V404_SYNTHETIC_FUNCTIONS)
        return 0;
    candidate.owner = owner;
    candidate.table = compiled;
    candidate.bound = 1u;
    for (i = 0; i < count; ++i) {
        candidate.approved[i] = compiled[i].fn;
        candidate.direct[i] = compiled[i].direct;
    }
    if (!verified_table(&candidate))
        return 0;
    *out = candidate;
    return 1;
}

static int proven_tcb(uint64_t offset) {
    return offset == UINT64_C(0x10e0) || offset == UINT64_C(0x1100) ||
           offset == UINT64_C(0x1120) || offset == UINT64_C(0x1160);
}

/* The guest return word MUST be validated with the SAME V390 lease
 * that owns the ensuing real generated call. V393 enters the pinned
 * scope before calling this preflight, and cannot unpin/remap it
 * between preflight and the native RcFn. This closes a V389 TOCTOU.
 */
typedef struct ShytV404ReturnPreflight {
    ShytNativeOsVmV388 *owner;
    uint64_t rsp;
    uint64_t expected_return;
} ShytV404ReturnPreflight;
static int guest_return_preflight(const BbCpu *cpu, void *context) {
    ShytV404ReturnPreflight *p = (ShytV404ReturnPreflight *)context;
    uint64_t ret = 0;
    if (!cpu || !p || !p->owner || cpu->r[RSP] != p->rsp ||
        p->rsp > UINT64_MAX - UINT64_C(8) ||
        !shyt_generated_active_v390() ||
        shyt_generated_owner_v392() != p->owner ||
        !shyt_generated_try_load_v390(p->rsp, 8, &ret) ||
        ret == 0)
        return 0;
    p->expected_return = ret;
    return 1;
}

int shyt_native_execution_try_v404(ShytNativeExecutionV404 *route,
    uint64_t offset, BbCpu *cpu) {
    size_t i;
    uint64_t rsp;
    ShytV404ReturnPreflight preflight = {0};
    int recovered = 0, result;
    RcFn selected = NULL;

    /* The V403 11-way membership alone is not proof of execution
     * semantics. Only the four already executed native TCB functions
     * have independent V404 runtime entry permission. */
    if (!cpu || !proven_tcb(offset) ||
        !shyt_v403_is_synthetic_candidate(offset) ||
        !verified_table(route))
        return SHYT_V404_DENIED;
    for (i = 0; i < SHYT_V404_SYNTHETIC_FUNCTIONS; ++i) {
        if (route->table[i].offset == offset) {
            selected = route->approved[i];
            break;
        }
    }
    if (!selected)
        return SHYT_V404_DENIED;
    rsp = cpu->r[RSP];
    if (rsp > UINT64_MAX - UINT64_C(8))
        return SHYT_V404_DENIED;
    preflight.owner = route->owner;
    preflight.rsp = rsp;
    result = shyt_generated_call_recoverable_v393(
        route->owner, selected, cpu, guest_return_preflight,
        &preflight, &recovered);
    if (result == SHYT_V393_DENIED)
        return SHYT_V404_DENIED;
    if (result != SHYT_V393_COMPLETED || recovered ||
        cpu->r[RSP] != rsp + UINT64_C(8) ||
        cpu->rip != preflight.expected_return ||
        shyt_generated_active_v390() ||
        shyt_generated_recovery_depth_v393())
        abort(); /* executed code broke a mandatory host invariant */
    return SHYT_V404_COMPLETED;
}
