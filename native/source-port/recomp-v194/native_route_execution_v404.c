/* SPDX-License-Identifier: GPL-2.0-or-later
 * V404: no use of guessed runtime pointers or fallback callbacks.
 * Source-locked 11-function invented-only evidence from V402/V403 CI.
 */
#include "native_route_execution_v404.h"
#include "native_only_approved_v402_generated.h"
#include "native_route_guard_v403_generated.h"
#include <stdlib.h>
extern void f_1000(BbCpu *);
extern void f_1020(BbCpu *);
extern void f_1040(BbCpu *);
extern void f_1060(BbCpu *);
extern void f_1080(BbCpu *);
extern void f_10a0(BbCpu *);
extern void f_10c0(BbCpu *);
extern void f_10e0(BbCpu *);
extern void f_1100(BbCpu *);
extern void f_1120(BbCpu *);
extern void f_1160(BbCpu *);

/* Linker-resolved symbols, not pointers vouched for by table metadata. */
static const RcFn linked_functions[] = {
    f_1000, f_1020, f_1040, f_1060, f_1080, f_10a0, f_10c0, f_10e0, f_1100, f_1120, f_1160
};

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
            f[i].fn != linked_functions[i] || !f[i].direct ||
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
    uint64_t offset;
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
    /* All five memory probes address [RDI]. Check the entire operand
     * before entering generated C. The VM pin protects mapping and
     * permissions, not contents; the caller owns CPU and return slot. */
    if (p->offset <= UINT64_C(0x1080)) {
        const uint64_t address = cpu->r[RDI];
        size_t width = 8u;
        unsigned access = SHYT_V386_READ | SHYT_V386_WRITE;
        if (p->offset != UINT64_C(0x1000)) {
            width = p->offset <= UINT64_C(0x1040) ? 16u : 32u;
            access = (p->offset == UINT64_C(0x1020) ||
                      p->offset == UINT64_C(0x1060)) ?
                     SHYT_V386_READ : SHYT_V386_WRITE;
        } else if (address & UINT64_C(7)) {
            return 0; /* V390 cannot implement a cross-word LOCK CAS. */
        }
        if (!shyt_generated_try_probe_v390(address, width, access))
            return 0;
        if ((access & SHYT_V386_WRITE) &&
            address < p->rsp + UINT64_C(8) &&
            p->rsp < address + (uint64_t)width)
            return 0; /* Do not overwrite our own return slot. */
    }
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
     * semantics. Admit only the four TCB probes and five guarded
     * memory probes; the two CALL RAX sites remain denied. */
    if (!cpu || shyt_generated_active_v390() ||
        shyt_generated_recovery_depth_v393() ||
        (!proven_tcb(offset) && (offset < UINT64_C(0x1000) ||
                                  offset > UINT64_C(0x1080))) ||
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
    preflight.offset = offset;
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
