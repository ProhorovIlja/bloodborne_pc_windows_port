/* SPDX-License-Identifier: GPL-2.0-or-later
 * V245: One ordered, immutable Win64 service bootstrap for AOT game code.
 * Original Windows-native RcApi -> V226 math -> V239 host clocks ->
 * ACTUAL bb_recomp_init callback. No EBOOT/PS4 ELF needed at runtime.
 */
#ifndef SHYT_NATIVE_AOT_SERVICES_BOOTSTRAP_V245_H
#define SHYT_NATIVE_AOT_SERVICES_BOOTSTRAP_V245_H
#include "native_math_rcapi_route_v226.h"
#include "native_clock_rcapi_route_v239.h"
#include "native_aot_direct_link_v259.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    ShytMathRcApiRoute math;
    ShytClockRouteV239 clock;
    const RcApi *published_api;
    const RcFunction *functions;
    size_t function_count;
} ShytAotServicesV245;

/* Services MUST live until process exit and be installed exactly once,
 * before starting game threads. Imported offsets are computed PRIVATELY
 * at build time from the user's game files; no runtime EBOOT loading.
 *
 * This initializer fails closed. If the second route cannot be installed
 * after the first was committed, it terminates the process rather than
 * leaving a global callback pointing at partially initialized state.
 */
int shyt_aot_services_bootstrap_v245(
    ShytAotServicesV245 *services,
    const RcApi *native_platform_api,
    const ShytMathImportTable *math_imports,
    const ShytClockTargetsV239 *clock_imports,
    ShytGuestMemoryPermit permit, void *permit_ctx,
    ShytMathFatalGuestMemory fault, void *fault_ctx,
    ShytMathMemoryPinEnter pin_enter, ShytMathMemoryPinLeave pin_leave,
    void *pin_ctx, RcInit real_recompiled_init);

/* V261: optional genuine AOT-to-AOT fastpath AFTER successful
 * shyt_aot_services_bootstrap_v245 and BEFORE game threads. Only the
 * owner's trusted exact-code attester can permit direct slots; all
 * unknown/patched functions remain indirect (NULL slot). NEVER use
 * a mock always-true callback against actual game functions. */
int shyt_aot_services_link_direct_v261(
    ShytAotServicesV245 *services,
    ShytDirectFunctionAttestV259 attester, void *attest_ctx,
    ShytDirectStatsV259 *stats);
#ifdef __cplusplus
}
#endif
#endif
