/* SPDX-License-Identifier: GPL-2.0-or-later
 * V245: Runtime-free AOT service chain to the real generated-code
 * initializer, no compatibility host and no retail executable in CI.
 */
#include "native_aot_services_bootstrap_v245.h"
#include "native_aot_table_audit_v257.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

int shyt_aot_services_bootstrap_v245(
    ShytAotServicesV245 *services,
    const RcApi *native_platform_api,
    const ShytMathImportTable *math_imports,
    const ShytClockTargetsV239 *clock_imports,
    ShytGuestMemoryPermit permit, void *permit_ctx,
    ShytMathFatalGuestMemory fault, void *fault_ctx,
    ShytMathMemoryPinEnter pin_enter, ShytMathMemoryPinLeave pin_leave,
    void *pin_ctx, RcInit real_recompiled_init)
{
    if (!services || !native_platform_api || !math_imports ||
        !clock_imports || !permit || !fault || !pin_enter || !pin_leave ||
        !real_recompiled_init || services->published_api ||
        native_platform_api->version != BB_RECOMP_API_VERSION ||
        !native_platform_api->image_base ||
        !native_platform_api->step || !native_platform_api->call ||
        !native_platform_api->tail || !native_platform_api->bail ||
        native_platform_api->image_base != math_imports->image_base ||
        native_platform_api->image_base != clock_imports->image_base ||
        !clock_imports->read_tsc_offset ||
        !clock_imports->get_tsc_frequency_offset ||
        clock_imports->read_tsc_offset == clock_imports->get_tsc_frequency_offset ||
        clock_imports->read_tsc_offset > UINT64_MAX - clock_imports->image_base ||
        clock_imports->get_tsc_frequency_offset > UINT64_MAX - clock_imports->image_base)
        return 0;

    /* Imported clock addresses must never shadow known math handler slots.
     * Reject the entire configuration BEFORE installing either global route. */
    for (size_t i = 0; i < 23; ++i) {
        if (!math_imports->entries[i].fn ||
            !math_imports->entries[i].offset ||
            math_imports->entries[i].offset > UINT64_MAX - math_imports->image_base ||
            math_imports->entries[i].offset == clock_imports->read_tsc_offset ||
            math_imports->entries[i].offset == clock_imports->get_tsc_frequency_offset)
            return 0;
        /* V267: an imported offset cannot name two different shims.
         * Equally, one math handler cannot claim multiple original
         * imports: the real V224 importer enforces both invariants.
         * Recheck here so an unchecked/corrupted private table cannot
         * bypass the single irreversible process-lifetime bootstrap. */
        for (size_t j = 0; j < i; ++j) {
            if (math_imports->entries[i].offset ==
                    math_imports->entries[j].offset ||
                math_imports->entries[i].fn ==
                    math_imports->entries[j].fn)
                return 0;
        }
    }

    /* Clock initialization is checked before installing the immutable math
     * route. It does NOT eliminate all possible later errors: fail closed. */
    shyt_win_clock_v236 preflight_clock;
    if (shyt_clock_initialize_v236(&preflight_clock)) return 0;

    if (!shyt_math_rcapi_route_v226_install_pinned(
        &services->math, native_platform_api, math_imports,
        permit, permit_ctx, fault, fault_ctx,
        pin_enter, pin_leave, pin_ctx))
        return 0;

    const RcApi *math_api = shyt_math_rcapi_route_v226_api(&services->math);
    if (!math_api ||
        !shyt_clock_rcapi_install_v239(
            &services->clock, math_api, clock_imports,
            permit, permit_ctx, fault, fault_ctx,
            pin_enter, pin_leave, pin_ctx)) {
        /* No process-safe uninstall of V226 exists once its callback is
         * published. Returning leaves a dangling route if caller frees
         * services; abort instead of risking a use-after-free. */
        abort();
    }

    services->published_api = shyt_clock_rcapi_api_v239(&services->clock);
    if (!services->published_api) abort();

    /* This IS the same contract a private native executable uses to
     * register its actual generated AOT functions; only the test fixture
     * supplies a synthetic implementation. No dynamic guest ELF loading. */
    size_t count=0;
    const RcFunction *functions = real_recompiled_init(
        services->published_api, &count);
    /* V257: a nonempty count is not sufficient: a corrupt function table
     * may contain null executable targets, wrapped offsets, duplicate
     * function entrypoints, or zero-sized generated code. In this process-
     * lifetime irreversible bootstrap, trap before publishing any table. */
    if (!shyt_aot_table_valid_v257(
            functions, count, native_platform_api->image_base))
        abort();
    services->functions=functions;
    services->function_count=count;
    return 1;
}

/* V261: enable actual RcFunction.direct slots only after owner-verified
 * exact original-game function hashes. No code hash, no direct dispatch.
 * Called before threads, and never without a valid installed AOT table.
 * This cannot verify code by itself; the caller must independently do so. */
int shyt_aot_services_link_direct_v261(
    ShytAotServicesV245 *services,
    ShytDirectFunctionAttestV259 attester, void *attest_ctx,
    ShytDirectStatsV259 *stats)
{
    if (!services || !services->published_api || !services->functions ||
        !services->function_count || !attester || !stats ||
        !services->published_api->image_base)
        return 0;
    return shyt_aot_activate_direct_slots_v259(
        services->functions, services->function_count,
        services->published_api->image_base, attester, attest_ctx, stats);
}
