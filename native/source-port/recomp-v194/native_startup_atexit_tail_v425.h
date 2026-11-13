/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_ATEXIT_TAIL_V425_H
#define SHYT_STARTUP_ATEXIT_TAIL_V425_H
#include "native_startup_atexit_v423.h"

/* Startup-only RcApi.tail adapter. Unlike RcApi.call, a generated tail
 * transfer already has a return word. No push or guest-memory write.
 * Trusted controller binds the actual active constructor and the tuple
 * after independently checking its tail edge. RcApi.tail does NOT carry
 * the source PC, so this cannot establish general origin-site integrity. */
typedef struct {
    uint32_t scope;
    ShytAtexitSiteV423 registration;
} ShytAtexitTailSiteV425;

static inline int shyt_atexit_tail_v425(ShytAtexitV423 *list,
    ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,
    const RcFunction *table,size_t count,const ShytAtexitTailSiteV425 *site,
    uint32_t scope,uint64_t stack_lo,uint64_t stack_hi) {
    if(!owner || !cpu || cpu!=expected || !site || !scope || scope!=site->scope ||
       cpu->rip!=site->registration.edge.target || stack_lo>=stack_hi ||
       stack_hi-stack_lo<8u || shyt_generated_owner_v392()!=owner ||
       shyt_generated_recovery_depth_v393()!=1u)return 0;
    const uint64_t sp=cpu->r[4];
    uint64_t next=0;
    if((sp&7u) || sp<stack_lo || sp>stack_hi-8u ||
       !shyt_generated_try_load_v390(sp,8,&next) || next!=site->registration.edge.next)
        return 0;
    if(!shyt_atexit_call_v423(list,owner,expected,cpu,table,count,
                             &site->registration,cpu->rip,next))return 0;
    /* Even a normal ABI error (e.g. capacity exhaustion) returns. */
    cpu->r[4]=sp+8u;
    return 1;
}
#endif
