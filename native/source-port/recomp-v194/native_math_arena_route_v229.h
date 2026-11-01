/* SPDX-License-Identifier: GPL-2.0-or-later
 * V229 Win64 integration: original RcApi V4 callback route pinned to a
 * V228 owner-managed guest arena. Build-time game import descriptors only.
 */
#ifndef SHYT_NATIVE_MATH_ARENA_ROUTE_V229_H
#define SHYT_NATIVE_MATH_ARENA_ROUTE_V229_H
#include "native_math_rcapi_route_v226.h"
#include "native_guest_arena_v228.h"
/* Set up ONCE before game worker threads, while the V228 arena is live.
 * The route and arena must outlive all guest call workers. The allocator
 * holds its SRW shared lock for the WHOLE checked import execution.
 */
int shyt_math_arena_route_v229_install(
    ShytMathRcApiRoute *route, const RcApi *original,
    const ShytMathImportTable *table, ShytGuestArenaV228 *arena,
    ShytMathFatalGuestMemory fault, void *fault_context);
#endif
