/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_NATIVE_STARTUP_CALL_V418_H
#define SHYT_NATIVE_STARTUP_CALL_V418_H
#include "full_cpu_abi_v194.h"
#include "native_host_recovery_v393.h"

/* The controller supplies a validated, sorted, immutable registry and an
 * approved edge. A denied call has no effects. A bad return is terminal:
 * generated code has already executed; do not retry or fall back. */
typedef struct { uint64_t target, next; } ShytStartupEdgeV418;
enum ShytStartupCallV418 { SHYT_STARTUP_DENIED, SHYT_STARTUP_RETURNED, SHYT_STARTUP_BAD_RETURN };
static inline RcFn shyt_startup_find_v418(const RcFunction *table,size_t count,uint64_t id) {
    size_t lo=0,hi=count;
    while(lo<hi){
        const size_t mid=lo+(hi-lo)/2;
        if(table[mid].offset<id)lo=mid+1;
        else hi=mid;
    }
    return lo<count && table[lo].offset==id ? table[lo].fn : NULL;
}
static inline enum ShytStartupCallV418 shyt_startup_call_v418(
    ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,
    const RcFunction *table,size_t count,const ShytStartupEdgeV418 *edge,
    uint64_t target,uint64_t next,uint64_t stack_lo,uint64_t stack_hi) {
    if(!owner || !cpu || cpu!=expected || !table || !count || !edge ||
       !target || !next || target==next || edge->target!=target || edge->next!=next ||
       stack_lo>=stack_hi || stack_hi-stack_lo<8u ||
       shyt_generated_owner_v392()!=owner || shyt_generated_recovery_depth_v393()!=1u)
        return SHYT_STARTUP_DENIED;
    const uint64_t sp=cpu->r[4];
    if((sp&7u) || sp<stack_lo+8u || sp>stack_hi)return SHYT_STARTUP_DENIED;
    const RcFn fn=shyt_startup_find_v418(table,count,target);
    if(!fn || !shyt_generated_try_probe_v390(sp-8u,8,SHYT_V386_READ|SHYT_V386_WRITE) ||
       !shyt_generated_try_store_v390(sp-8u,8,next))return SHYT_STARTUP_DENIED;
    cpu->r[4]=sp-8u;
    cpu->rip=target;
    fn(cpu);
    return cpu->rip==next && cpu->r[4]==sp ? SHYT_STARTUP_RETURNED : SHYT_STARTUP_BAD_RETURN;
}
#endif
