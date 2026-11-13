/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_MUTEX_PLAN_V419_H
#define SHYT_STARTUP_MUTEX_PLAN_V419_H
#include "native_startup_mutex_routes_v416.h"

enum { SHYT_MUTEX_PLAN_MAX_V419=16 };
typedef struct {
    size_t object;
    ShytStartupMutexSiteV413 call[4];
} ShytMutexStepV419;
typedef struct { size_t step; unsigned op; } ShytMutexCursorV419;

static inline int shyt_mutex_plan_valid_v419(const ShytMutexStepV419 *plan,
    size_t steps, size_t objects) {
    if(!plan || !steps || steps>SHYT_MUTEX_PLAN_MAX_V419 || !objects || objects>64)return 0;
    for(size_t i=0;i<steps;++i) {
        if(plan[i].object>=objects)return 0;
        for(size_t j=0;j<i;++j)if(plan[j].object==plan[i].object)return 0;
        for(unsigned k=0;k<4;++k) {
            const ShytStartupMutexSiteV413 *site=&plan[i].call[k];
            if((unsigned)site->op!=k || !site->target || !site->next ||
               site->target==site->next)return 0;
            for(unsigned j=0;j<k;++j)if(plan[i].call[j].next==site->next)return 0;
        }
    }
    return 1;
}
/* Single startup controller. The cursor begins at zero for the actual
 * constructor invocation. The controller owns immutable, validated
 * steps and objects; a declined route or nonzero ABI result does not
 * advance the cursor. Caller must stop on ABI error or incomplete plan
 * before counting the constructor as verified. No general pthread ABI. */
static inline int shyt_mutex_plan_call_v419(const ShytMutexStepV419 *plan,
    size_t steps,ShytMutexCursorV419 *cursor,ShytStartupMutexStateV413 *objects,
    size_t count,BbCpu *expected,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!plan || !cursor || !objects || !steps || steps>SHYT_MUTEX_PLAN_MAX_V419 ||
       !count || count>64 || cursor->step>=steps || cursor->op>=4)return 0;
    const ShytMutexStepV419 *step=&plan[cursor->step];
    if(step->object>=count || (unsigned)step->call[cursor->op].op!=cursor->op ||
       !shyt_mutex_call_v413(&objects[step->object],&step->call[cursor->op],
                           expected,cpu,target,next))return 0;
    if(!cpu->r[0] && ++cursor->op==4) {
        cursor->op=0;
        ++cursor->step;
    }
    return 1;
}
static inline int shyt_mutex_plan_complete_v419(const ShytMutexCursorV419 *cursor,size_t steps) {
    return cursor && steps && steps<=SHYT_MUTEX_PLAN_MAX_V419 &&
           cursor->step==steps && !cursor->op;
}
#endif
