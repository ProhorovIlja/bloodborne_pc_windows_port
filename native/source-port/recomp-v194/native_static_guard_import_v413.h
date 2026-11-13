/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_NATIVE_STATIC_GUARD_IMPORT_V413_H
#define SHYT_NATIVE_STATIC_GUARD_IMPORT_V413_H
#include "native_static_guard_v413.h"
#include "full_cpu_abi_v194.h"
#include "native_host_recovery_v393.h"

/* A trusted active caller selects an immutable exact site. This is an
 * adapter, not permission to infer a service from a target alone.
 * Single controller owns the guard and CPU for the entire operation. */
typedef struct {
    uint64_t target,next,guard;
    enum ShytGuardAction action;
} ShytGuardSiteV413;
static inline int shyt_guard_call_v413(ShytNativeOsVmV388 *owner,
    const ShytGuardSiteV413 *site,BbCpu *expected_cpu,BbCpu *cpu,
    uint64_t target,uint64_t next) {
    uint64_t old=0,word=0;
    if(!owner || !site || !cpu || cpu!=expected_cpu || !target || !next ||
       target==next || target!=site->target || next!=site->next ||
       !site->guard || site->guard!=cpu->r[7] || (site->guard&7u) ||
       site->guard>UINT64_MAX-8u || cpu->r[4]>UINT64_MAX-8u ||
       (site->guard<cpu->r[4]+8u && cpu->r[4]<site->guard+8u) ||
       shyt_generated_owner_v392()!=owner ||
       shyt_generated_recovery_depth_v393()!=1u ||
       !shyt_generated_try_probe_v390(site->guard,8,SHYT_V386_READ|SHYT_V386_WRITE) ||
       !shyt_generated_try_load_v390(site->guard,8,&old))return 0;
    const enum ShytGuardResult result=shyt_guard_transition_v413(old,site->action,&word);
    if(result==SHYT_GUARD_REFUSED)return 0;
    if(word!=old && !shyt_generated_try_store_v390(site->guard,8,word))return 0;
    if(site->action==SHYT_GUARD_ACQUIRE)cpu->r[0]=(uint64_t)result;
    cpu->rip=next;
    return 1;
}
#endif
