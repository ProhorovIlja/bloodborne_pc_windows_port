/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_host_recovery_v393.h"
#include <setjmp.h>
#include <stdlib.h>
typedef struct ShytRecoveryFrameV393 {
    jmp_buf landing;
    struct ShytRecoveryFrameV393 *previous;
    ShytNativeOsVmV388 *owner;
    volatile int reason;
} ShytRecoveryFrameV393;
static _Thread_local ShytRecoveryFrameV393 *current_frame_v393;
static _Thread_local unsigned frame_depth_v393;
#define SHYT_V393_MAX_DEPTH 16u
unsigned shyt_generated_recovery_depth_v393(void) {
    return frame_depth_v393;
}
_Noreturn void shyt_generated_raise_v393(int reason) {
    ShytRecoveryFrameV393 *frame=current_frame_v393;
    if(reason<=0 || !frame || !frame_depth_v393 ||
       shyt_generated_owner_v392()!=frame->owner)abort();
    frame->reason=reason;
    longjmp(frame->landing,1);
    abort();
}
int shyt_generated_call_recoverable_v393(
    ShytNativeOsVmV388 *owner,ShytGeneratedFnV392 fn,BbCpu *cpu,
    ShytGeneratedPreflightV392 preflight,void *context,
    int *recovery_code) {
    ShytGeneratedScopeV392 scope={0};
    ShytRecoveryFrameV393 frame;
    volatile int result=SHYT_V393_DENIED;
    if(recovery_code)*recovery_code=0;
    if(!owner || !fn || !cpu ||
       frame_depth_v393>=SHYT_V393_MAX_DEPTH ||
       !shyt_generated_scope_begin_v392(&scope,owner))return SHYT_V393_DENIED;
    frame.previous=current_frame_v393;
    frame.owner=owner;
    frame.reason=0;
    current_frame_v393=&frame;
    ++frame_depth_v393;
    /* C11 requires setjmp to be the controlling expression of if.
     * scope and frame pointers are initialized before setjmp, and the
     * only frame member modified by raise is VOLATILE reason.
     * 'result' is also VOLATILE to remain defined across longjmp.
     */
    if(setjmp(frame.landing)==0) {
        if(!preflight || preflight(cpu,context)) {
            fn(cpu);
            result=SHYT_V393_COMPLETED;
        }
    }else{
        if(frame.reason<=0)abort();
        result=SHYT_V393_RECOVERED;
    }
    if(current_frame_v393!=&frame || !frame_depth_v393)abort();
    current_frame_v393=frame.previous;
    --frame_depth_v393;
    /* A recovery is never a success if the V390/392 backing pin could
     * not be released. Borrowed scopes unpin only in the outer scope. */
    if(!shyt_generated_scope_end_v392(&scope))abort();
    if(recovery_code && result==SHYT_V393_RECOVERED)
        *recovery_code=frame.reason;
    return (int)result;
}
