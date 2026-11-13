/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_rcapi_v436.h"
#include <stdlib.h>

typedef struct {
    ShytStartupDispatchV435 *dispatch;
    uint32_t ordinal;
} ShytActiveCallV436;
static _Thread_local const ShytActiveCallV436 *active_v436;

void shyt_startup_rcapi_call_v436(BbCpu *cpu,uint64_t target,uint64_t next) {
    const ShytActiveCallV436 *active=active_v436;
    if(!active || shyt_generated_recovery_depth_v393()!=1u ||
       shyt_generated_owner_v392()!=active->dispatch->owner)abort();
    const enum ShytStartupCallV418 result=shyt_startup_dispatch_v435(
        active->dispatch,cpu,active->ordinal,target,next);
    if(result==SHYT_STARTUP_RETURNED)return;
    shyt_generated_raise_v393(result==SHYT_STARTUP_BAD_RETURN ?
        SHYT_V436_CALL_BAD_RETURN : SHYT_V436_CALL_DENIED);
}

int shyt_startup_rcapi_run_v436(ShytStartupDispatchV435 *dispatch,
    uint32_t ordinal,RcFn driver,int *reason) {
    if(reason)*reason=0;
    if(active_v436 || shyt_generated_recovery_depth_v393()!=0u ||
       !dispatch || !dispatch->owner || !dispatch->cpu || !dispatch->routes ||
       !dispatch->bindings || !dispatch->count ||
       dispatch->count>SHYT_STARTUP_EDGES_MAX_V426 || dispatch->terminal ||
       !driver || !ordinal || ordinal>SHYT_CTOR_LIMIT_V427)
        return SHYT_V393_DENIED;
    const ShytActiveCallV436 active={dispatch,ordinal};
    active_v436=&active;
    const int result=shyt_generated_call_recoverable_v393(
        dispatch->owner,driver,dispatch->cpu,NULL,NULL,reason);
    active_v436=NULL;
    if(result==SHYT_V393_RECOVERED)dispatch->terminal=1;
    return result;
}
