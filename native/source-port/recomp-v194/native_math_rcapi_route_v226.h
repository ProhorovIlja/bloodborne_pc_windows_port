/* SPDX-License-Identifier: GPL-2.0-or-later
 * V226: opt-in RcApi V4 math routing. Install before game worker threads.
 * No original PS4 EBOOT runtime dependency.
 */
#ifndef SHYT_NATIVE_MATH_RCAPI_ROUTE_V226_H
#define SHYT_NATIVE_MATH_RCAPI_ROUTE_V226_H
#include "native_math_import_dispatch_v224.h"
#include "recomp/rc.h"
#include <stdint.h>

/* Called for a KNOWN math target and unsafe guest memory. MUST terminate
 * guest execution (e.g. longjmp to validated fault boundary). If it
 * returns, the dispatcher aborts the process rather than corrupt memory.
 */
typedef void (*ShytMathFatalGuestMemory)(BbCpu *cpu, uint64_t target,
                                        uint64_t next, void *ctx);
/* Callback holding a verified host guest-allocation lease; its lifetime
 * must span the entire math import. Fault handlers run AFTER release. */
typedef int (*ShytMathMemoryPinEnter)(void *ctx);
typedef void (*ShytMathMemoryPinLeave)(void *ctx);
typedef struct {
    RcApi api;
    RcApi original;
    ShytMathImportTable table;
    ShytGuestMemoryPermit permit;
    void *permit_ctx;
    ShytMathFatalGuestMemory fault;
    void *fault_ctx;
    ShytMathMemoryPinEnter pin_enter;
    ShytMathMemoryPinLeave pin_leave;
    void *pin_ctx;
} ShytMathRcApiRoute;

/* Exactly one immutable route per process, installed single-threaded before
 * worker threads start; caller owns route and its callback contexts for
 * the entire process lifetime. Never reinstall into the active object. */
int shyt_math_rcapi_route_v226_install(ShytMathRcApiRoute *route,
       const RcApi *upstream, const ShytMathImportTable *table,
       ShytGuestMemoryPermit permit, void *permit_ctx,
       ShytMathFatalGuestMemory fault, void *fault_ctx);
/* V229: requires pin callbacks even in synthetic fixtures. The V226
 * unpinned installer is disabled and always returns 0.
 * PIN MUST exclude VirtualFree/VirtualProtect until LEAVE. If enter fails,
 * a mandatory guest fault handler is invoked, never the old callback. */
int shyt_math_rcapi_route_v226_install_pinned(ShytMathRcApiRoute *route,
       const RcApi *upstream, const ShytMathImportTable *table,
       ShytGuestMemoryPermit permit, void *permit_ctx,
       ShytMathFatalGuestMemory fault, void *fault_ctx,
       ShytMathMemoryPinEnter pin_enter, ShytMathMemoryPinLeave pin_leave,
       void *pin_ctx);
/* Pass this API to the recompiled game's bb_recomp_init only after install. */
const RcApi *shyt_math_rcapi_route_v226_api(const ShytMathRcApiRoute *route);
#endif
