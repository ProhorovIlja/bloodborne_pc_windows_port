/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_RETAIL_PLAN_V439_H
#define SHYT_STARTUP_RETAIL_PLAN_V439_H
#include "native_startup_entry_v438.h"
#include "native_startup_sequence_v437.h"

/* Rows must come from an independently audited constructor order and remain
 * immutable and disjoint from mutable state. Repeated target IDs are valid.
 * A trusted post hook checks import/lock conditions while the VM is pinned.
 * Do not reuse stopped state. No static closure or retail attestation here. */
static inline enum ShytReplayResultV437 shyt_startup_retail_plan_v439(
    ShytStartupDispatchV435 *state,const ShytCtorRowV427 *rows,uint32_t first,
    size_t count,uint64_t sentinel,ShytCtorPostV439 post,void *context,
    ShytReplayReportV437 *report) {
    if(!report)return SHYT_REPLAY_REFUSED;
    *report=(ShytReplayReportV437){0};
    if(!state || state->terminal || !state->cpu || !state->owner || !state->registry ||
       !state->registry_count || state->registry_count>SHYT_CTOR_REG_LIMIT_V427 ||
       !rows || !post || !first || first>SHYT_CTOR_LIMIT_V427 || !count ||
       count>SHYT_CTOR_LIMIT_V427-first+1u || !sentinel ||
       shyt_generated_recovery_depth_v393() ||
       shyt_startup_find_v418(state->registry,state->registry_count,sentinel))
        return SHYT_REPLAY_REFUSED;
    for(size_t i=0;i<count;++i) {
        if(rows[i].ordinal!=first+i || !rows[i].id ||
           !shyt_startup_find_v418(state->registry,state->registry_count,rows[i].id))
            return SHYT_REPLAY_REFUSED;
    }
    for(size_t i=0;i<count;++i) {
        int reason=0;
        if(shyt_startup_entry_checked_v439(state,rows[i].ordinal,rows[i].id,
              sentinel,post,context,&reason)!=SHYT_V393_COMPLETED) {
            state->terminal=1;
            report->stopped_at=rows[i].ordinal;
            report->reason=reason ? reason : SHYT_V437_ENTRY_DENIED;
            return SHYT_REPLAY_STOPPED;
        }
        ++report->returned;
    }
    return SHYT_REPLAY_COMPLETE;
}
#endif
