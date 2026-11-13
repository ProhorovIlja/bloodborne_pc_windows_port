/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_SEQUENCE_V437_H
#define SHYT_STARTUP_SEQUENCE_V437_H
#include "native_startup_rcapi_v436.h"

typedef struct { uint32_t ordinal; RcFn driver; uint64_t return_ip; } ShytReplayStepV437;
enum ShytReplayResultV437 {
    SHYT_REPLAY_REFUSED, SHYT_REPLAY_COMPLETE, SHYT_REPLAY_STOPPED
};
typedef struct { size_t returned; uint32_t stopped_at; int reason; } ShytReplayReportV437;
enum { SHYT_V437_OUTER_RETURN = 43701, SHYT_V437_ENTRY_DENIED = 43702 };

/* Trusted host supplies immutable, disjoint steps and report storage.
 * Preserve one VM and CPU across the prefix. The driver is responsible
 * for its return word and any import/lock postconditions beyond RIP/RSP.
 * A stop is terminal; guest memory changes are not rolled back. */
static inline enum ShytReplayResultV437 shyt_startup_sequence_v437(
    ShytStartupDispatchV435 *state,const ShytReplayStepV437 *steps,
    uint32_t first,size_t count,ShytReplayReportV437 *report) {
    if(!report)return SHYT_REPLAY_REFUSED;
    *report=(ShytReplayReportV437){0};
    if(!state || !state->cpu || state->terminal || !steps || !first ||
       first>SHYT_CTOR_LIMIT_V427 || !count || count>SHYT_CTOR_LIMIT_V427-first+1u ||
       shyt_generated_recovery_depth_v393()!=0u)
        return SHYT_REPLAY_REFUSED;
    for(size_t i=0;i<count;++i)
        if(steps[i].ordinal!=first+i || !steps[i].driver || !steps[i].return_ip)
            return SHYT_REPLAY_REFUSED;
    for(size_t i=0;i<count;++i) {
        const uint64_t sp=state->cpu->r[4];
        int reason=0;
        const int result=shyt_startup_rcapi_run_v436(state,steps[i].ordinal,steps[i].driver,&reason);
        if(result!=SHYT_V393_COMPLETED || state->cpu->rip!=steps[i].return_ip ||
           state->cpu->r[4]!=sp) {
            state->terminal=1;
            report->stopped_at=steps[i].ordinal;
            report->reason=result==SHYT_V393_COMPLETED ? SHYT_V437_OUTER_RETURN :
                reason ? reason : SHYT_V437_ENTRY_DENIED;
            return SHYT_REPLAY_STOPPED;
        }
        ++report->returned;
    }
    return SHYT_REPLAY_COMPLETE;
}
#endif
