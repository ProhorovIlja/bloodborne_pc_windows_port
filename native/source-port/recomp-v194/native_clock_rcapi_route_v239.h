/* SPDX-License-Identifier: GPL-2.0-or-later
 * V239: bind two verified PS4-named clock imports to Windows host clocks.
 * Exact offsets are PRIVATE build-time inputs, never hardcoded or loaded
 * from a PS4 ELF at runtime. Install single-threaded before bb_recomp_init.
 */
#ifndef SHYT_NATIVE_CLOCK_RCAPI_ROUTE_V239_H
#define SHYT_NATIVE_CLOCK_RCAPI_ROUTE_V239_H
#include "native_win_clock_v236.h"
#include "recomp/rc.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef int (*ShytClockPermit)(void *ctx, uint64_t address, size_t len, int write);
typedef void (*ShytClockFatal)(BbCpu *cpu, uint64_t target, uint64_t next, void *ctx);
typedef int (*ShytClockPinEnter)(void *ctx);
typedef void (*ShytClockPinLeave)(void *ctx);

typedef struct {
    uint64_t image_base;
    uint64_t read_tsc_offset;
    uint64_t get_tsc_frequency_offset;
} ShytClockTargetsV239;

typedef struct {
    RcApi api;
    RcApi previous;
    shyt_win_clock_v236 clock;
    ShytClockTargetsV239 targets;
    ShytClockPermit permit;
    void *permit_ctx;
    ShytClockFatal fatal_guest;
    void *fatal_ctx;
    ShytClockPinEnter pin_enter;
    ShytClockPinLeave pin_leave;
    void *pin_ctx;
} ShytClockRouteV239;

/* The previous RcApi may already be the V226 math route: unknown clock
 * calls fall through without changing CPU registers or guest memory. */
int shyt_clock_rcapi_install_v239(ShytClockRouteV239 *route,
        const RcApi *previous, const ShytClockTargetsV239 *targets,
        ShytClockPermit permit, void *permit_ctx,
        ShytClockFatal fatal_guest, void *fatal_ctx,
        ShytClockPinEnter pin_enter, ShytClockPinLeave pin_leave,
        void *pin_ctx);
const RcApi *shyt_clock_rcapi_api_v239(const ShytClockRouteV239 *route);
#ifdef __cplusplus
}
#endif
#endif
