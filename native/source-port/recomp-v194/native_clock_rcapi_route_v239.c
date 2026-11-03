/* SPDX-License-Identifier: GPL-2.0-or-later
 * V239: real RcApi V4 call-chain integration of the two proven clock
 * signatures. No PS4 runtime loader, no hard-coded import addresses.
 */
#include "native_clock_rcapi_route_v239.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define SHYT_GUEST_TSC_HZ_V239 UINT64_C(1600000000)
static _Atomic(ShytClockRouteV239 *) g_clock_route = ATOMIC_VAR_INIT(NULL);

static void clock_call_v239(BbCpu *cpu, uint64_t target, uint64_t next) {
    ShytClockRouteV239 *r = atomic_load_explicit(&g_clock_route, memory_order_acquire);
    if (!r) abort(); /* never publish the wrapper before installing it */
    const uint64_t read_tsc = r->targets.image_base + r->targets.read_tsc_offset;
    const uint64_t frequency = r->targets.image_base + r->targets.get_tsc_frequency_offset;
    if (target != read_tsc && target != frequency) {
        r->previous.call(cpu, target, next);
        return;
    }
    /* Fail CLOSED for a known clock import if the allocation lease cannot
     * be acquired. A malicious/invalid guest stack must not be dereferenced.
     * The callback may longjmp, so always release the lease before fault. */
    if (!r->pin_enter(r->pin_ctx)) {
        r->fatal_guest(cpu, target, next, r->fatal_ctx);
        abort();
    }
    uint64_t value = SHYT_GUEST_TSC_HZ_V239;
    int valid = cpu && next && cpu->r[RSP] >= 8 &&
        r->permit(r->permit_ctx, cpu->r[RSP] - 8, sizeof(uint64_t), 1);
    if (valid && target == read_tsc) {
        if (shyt_clock_ticks_v236(&r->clock, SHYT_GUEST_TSC_HZ_V239, &value))
            valid = 0;
    }
    if (valid) {
        /* Same guest SysV immediate-return semantics as V224 math bridge.
         * All checks precede modification. Existing RSP stays unchanged. */
        const uint64_t slot = cpu->r[RSP] - 8;
        memcpy((void *)(uintptr_t)slot, &next, sizeof(next));
        cpu->r[RAX] = value;
        cpu->rip = next;
    }
    r->pin_leave(r->pin_ctx);
    if (valid) return;
    r->fatal_guest(cpu, target, next, r->fatal_ctx);
    abort();
}

int shyt_clock_rcapi_install_v239(ShytClockRouteV239 *route,
        const RcApi *previous, const ShytClockTargetsV239 *targets,
        ShytClockPermit permit, void *permit_ctx,
        ShytClockFatal fatal_guest, void *fatal_ctx,
        ShytClockPinEnter pin_enter, ShytClockPinLeave pin_leave,
        void *pin_ctx) {
    if (!route || !previous || !targets || !permit || !fatal_guest ||
        !pin_enter || !pin_leave || previous->version != BB_RECOMP_API_VERSION ||
        !previous->image_base || !previous->call || !previous->step ||
        !previous->tail || !previous->bail ||
        previous->call == clock_call_v239 ||
        previous->image_base != targets->image_base ||
        !targets->read_tsc_offset || !targets->get_tsc_frequency_offset ||
        targets->read_tsc_offset == targets->get_tsc_frequency_offset ||
        targets->read_tsc_offset > UINT64_MAX - targets->image_base ||
        targets->get_tsc_frequency_offset > UINT64_MAX - targets->image_base ||
        atomic_load_explicit(&g_clock_route, memory_order_acquire)) return 0;
    shyt_win_clock_v236 clock;
    if (shyt_clock_initialize_v236(&clock)) return 0;
    ShytClockRouteV239 candidate;
    memset(&candidate, 0, sizeof(candidate));
    candidate.previous = *previous;
    candidate.api = *previous;
    candidate.api.call = clock_call_v239;
    candidate.targets = *targets;
    candidate.clock = clock;
    candidate.permit = permit;
    candidate.permit_ctx = permit_ctx;
    candidate.fatal_guest = fatal_guest;
    candidate.fatal_ctx = fatal_ctx;
    candidate.pin_enter = pin_enter;
    candidate.pin_leave = pin_leave;
    candidate.pin_ctx = pin_ctx;
    *route = candidate;
    ShytClockRouteV239 *expected = NULL;
    if (!atomic_compare_exchange_strong_explicit(
        &g_clock_route, &expected, route, memory_order_release, memory_order_relaxed))
        return 0;  /* never replace active callback */
    return 1;
}

const RcApi *shyt_clock_rcapi_api_v239(const ShytClockRouteV239 *route) {
    return route && atomic_load_explicit(&g_clock_route, memory_order_acquire) == route
        ? &route->api : NULL;
}
