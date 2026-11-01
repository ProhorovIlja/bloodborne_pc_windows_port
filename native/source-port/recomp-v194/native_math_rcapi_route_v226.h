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
typedef struct {
    RcApi api;
    RcApi original;
    ShytMathImportTable table;
    ShytGuestMemoryPermit permit;
    void *permit_ctx;
    ShytMathFatalGuestMemory fault;
    void *fault_ctx;
} ShytMathRcApiRoute;

/* Exactly one immutable route per process, installed single-threaded before
 * worker threads start; caller owns route and its callback contexts for
 * the entire process lifetime. Never reinstall into the active object. */
int shyt_math_rcapi_route_v226_install(ShytMathRcApiRoute *route,
       const RcApi *upstream, const ShytMathImportTable *table,
       ShytGuestMemoryPermit permit, void *permit_ctx,
       ShytMathFatalGuestMemory fault, void *fault_ctx);
/* Pass this API to the recompiled game's bb_recomp_init only after install. */
const RcApi *shyt_math_rcapi_route_v226_api(const ShytMathRcApiRoute *route);
#endif
