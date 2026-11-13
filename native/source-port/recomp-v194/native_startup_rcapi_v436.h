/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_RCAPI_V436_H
#define SHYT_STARTUP_RCAPI_V436_H
#include "native_startup_dispatch_v435.h"

enum {
    SHYT_V436_CALL_DENIED=43601,
    SHYT_V436_CALL_BAD_RETURN=43602
};

/* For an RcApi.call or a trusted router's native-only branch. Outside the
 * wrapper, use is fatal. No interpreter path and no C++/resource unwinding. */
void shyt_startup_rcapi_call_v436(BbCpu *cpu,uint64_t target,uint64_t next);

/* The host supplies the current constructor ordinal and its audited driver.
 * The driver checks the top-level return and other replay postconditions.
 * A cooperative escape poisons this dispatcher; discard the replay state.
 * No guest code may choose scope or modify the frozen V435 routes. */
int shyt_startup_rcapi_run_v436(ShytStartupDispatchV435 *dispatch,
    uint32_t ordinal,RcFn driver,int *reason);
#endif
