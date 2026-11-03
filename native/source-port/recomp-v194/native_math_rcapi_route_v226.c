/* SPDX-License-Identifier: GPL-2.0-or-later
 * V226: guarded RcApi math callback router. Other calls are unchanged.
 * Uses the original pinned upstream RcApi V4 contract.
 */
#include "native_math_rcapi_route_v226.h"
#include <stdatomic.h>
#include <string.h>
#include <stdlib.h>

static _Atomic(ShytMathRcApiRoute *) g_active = ATOMIC_VAR_INIT(NULL);

static void math_first_call(BbCpu *cpu, uint64_t target, uint64_t next) {
    ShytMathRcApiRoute *route =
        atomic_load_explicit(&g_active, memory_order_acquire);
    if (!route) return; /* API cannot be published before install */
    /* V252: this callback receives ALL AOT imported calls, not only math.
     * Never acquire a guest allocation pin or fault a NON-math import.
     * The original code pinned on every call and wrongly aborted on lock
     * contention even for targets that do not read guest memory here.
     * Route table is immutable and process-lifetime-pinned after install. */
    int recognized = 0;
    for (size_t i=0; i<23; ++i) {
        if (route->table.entries[i].fn &&
            route->table.entries[i].offset <=
                UINT64_MAX - route->table.image_base &&
            route->table.image_base + route->table.entries[i].offset == target) {
            recognized = 1;
            break;
        }
    }
    if (!recognized) {
        route->original.call(cpu, target, next);
        return;
    }
    if (!route->pin_enter(route->pin_ctx)) {
        route->fault(cpu, target, next, route->fault_ctx);
        abort();
    }
    int result = shyt_math_import_v224_try_call_checked(
        &route->table, cpu, target, next, route->permit, route->permit_ctx);
    /* Release the pin BEFORE calling fault (which may longjmp), or fallback
     * to legacy RcApi.call. Never leave a pinned lock held across a trap. */
    route->pin_leave(route->pin_ctx);
    if (result > 0) return;
    if (result < 0) {
        /* Recognized but invalid: MUST NOT call legacy unchecked import. */
        route->fault(cpu, target, next, route->fault_ctx);
        abort(); /* A returning fault callback must not resume guest code */
    }
    /* Unknown target: original callback receives unmodified CPU state. */
    route->original.call(cpu, target, next);
}

int shyt_math_rcapi_route_v226_install_pinned(ShytMathRcApiRoute *route,
       const RcApi *upstream, const ShytMathImportTable *table,
       ShytGuestMemoryPermit permit, void *permit_ctx,
       ShytMathFatalGuestMemory fault, void *fault_ctx,
       ShytMathMemoryPinEnter pin_enter, ShytMathMemoryPinLeave pin_leave,
       void *pin_ctx) {
    if (!route || !upstream || !table || !permit || !fault ||
        !pin_enter || !pin_leave ||
        upstream->version != BB_RECOMP_API_VERSION || !upstream->call ||
        !upstream->step || !upstream->tail || !upstream->bail ||
        upstream->image_base != table->image_base ||
        upstream->call == math_first_call) return 0;
    /* Never mutate a live installed route on attempted reconfiguration. */
    if (atomic_load_explicit(&g_active, memory_order_acquire)) return 0;
    ShytMathRcApiRoute candidate;
    memset(&candidate, 0, sizeof(candidate));
    candidate.original = *upstream;
    candidate.api = *upstream;
    candidate.api.call = math_first_call;
    candidate.table = *table;
    candidate.permit = permit;
    candidate.permit_ctx = permit_ctx;
    candidate.fault = fault;
    candidate.fault_ctx = fault_ctx;
    candidate.pin_enter = pin_enter;
    candidate.pin_leave = pin_leave;
    candidate.pin_ctx = pin_ctx;
    *route = candidate;
    ShytMathRcApiRoute *expected = NULL;
    if (!atomic_compare_exchange_strong_explicit(
        &g_active, &expected, route, memory_order_release,
        memory_order_relaxed)) return 0;
    return 1;
}

/* Refuse old route without an allocation-lifetime lease. */
int shyt_math_rcapi_route_v226_install(ShytMathRcApiRoute *route,
       const RcApi *upstream, const ShytMathImportTable *table,
       ShytGuestMemoryPermit permit, void *permit_ctx,
       ShytMathFatalGuestMemory fault, void *fault_ctx) {
    (void)route; (void)upstream; (void)table;
    (void)permit; (void)permit_ctx; (void)fault; (void)fault_ctx;
    return 0;
}

const RcApi *shyt_math_rcapi_route_v226_api(
        const ShytMathRcApiRoute *route) {
    return route && atomic_load_explicit(
        &g_active, memory_order_acquire) == route ? &route->api : NULL;
}
