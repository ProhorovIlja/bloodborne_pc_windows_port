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
    int result = shyt_math_import_v224_try_call_checked(
        &route->table, cpu, target, next, route->permit, route->permit_ctx);
    if (result > 0) return;
    if (result < 0) {
        /* Recognized but invalid: MUST NOT call legacy unchecked import. */
        route->fault(cpu, target, next, route->fault_ctx);
        abort(); /* A returning fault callback must not resume guest code */
    }
    /* Unknown target: original callback receives unmodified CPU state. */
    route->original.call(cpu, target, next);
}

int shyt_math_rcapi_route_v226_install(ShytMathRcApiRoute *route,
       const RcApi *upstream, const ShytMathImportTable *table,
       ShytGuestMemoryPermit permit, void *permit_ctx,
       ShytMathFatalGuestMemory fault, void *fault_ctx) {
    if (!route || !upstream || !table || !permit || !fault ||
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
    *route = candidate;
    ShytMathRcApiRoute *expected = NULL;
    if (!atomic_compare_exchange_strong_explicit(
        &g_active, &expected, route, memory_order_release,
        memory_order_relaxed)) return 0;
    return 1;
}

const RcApi *shyt_math_rcapi_route_v226_api(
        const ShytMathRcApiRoute *route) {
    return route && atomic_load_explicit(
        &g_active, memory_order_acquire) == route ? &route->api : NULL;
}
