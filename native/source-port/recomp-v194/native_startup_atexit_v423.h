/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_ATEXIT_V423_H
#define SHYT_STARTUP_ATEXIT_V423_H
#include "native_startup_call_v418.h"
enum { SHYT_ATEXIT_MAX_V423=256 };
typedef struct { uint64_t fn,object,dso; } ShytDtorV423;
typedef struct {
    ShytDtorV423 entries[SHYT_ATEXIT_MAX_V423];
    size_t count;
    unsigned draining, failed;
} ShytAtexitV423;
typedef struct { ShytStartupEdgeV418 edge; ShytDtorV423 tuple; } ShytAtexitSiteV423;
typedef int (*ShytDtorInvokeV423)(void *,ShytDtorV423);

/* Single-controller startup subset: exact non-null registered tuple,
 * no guest-to-host pointer conversion or registration during drain. */
static inline int shyt_atexit_call_v423(ShytAtexitV423 *list,
    ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,
    const RcFunction *table,size_t count,const ShytAtexitSiteV423 *site,
    uint64_t target,uint64_t next) {
    if(!list || list->draining || list->failed || list->count>SHYT_ATEXIT_MAX_V423 ||
       !owner || !cpu || cpu!=expected || !site || !table || !count ||
       !target || !next || target==next || site->edge.target!=target || site->edge.next!=next ||
       shyt_generated_owner_v392()!=owner || shyt_generated_recovery_depth_v393()!=1u)return 0;
    const ShytDtorV423 t=site->tuple;
    if(!t.fn || !t.object || !t.dso || cpu->r[7]!=t.fn || cpu->r[6]!=t.object ||
       cpu->r[2]!=t.dso || !shyt_startup_find_v418(table,count,t.fn) ||
       !shyt_generated_try_probe_v390(t.object,1,SHYT_V386_READ) ||
       !shyt_generated_try_probe_v390(t.dso,1,SHYT_V386_READ))return 0;
    cpu->r[0]=UINT32_MAX;
    if(list->count<SHYT_ATEXIT_MAX_V423) {
        list->entries[list->count++]=t;
        cpu->r[0]=0;
    }
    cpu->rip=next;
    return 1;
}

/* Control thread calls outside the VM pin. Callback must return normally
 * from its own recovery scope. Consume before invocation; after a failed
 * destructor, stop and poison this list rather than retry mutated state. */
static inline int shyt_atexit_finalize_v423(ShytAtexitV423 *list,uint64_t dso,
    ShytDtorInvokeV423 invoke,void *context) {
    if(!list || !invoke || list->draining || list->failed ||
       list->count>SHYT_ATEXIT_MAX_V423 || shyt_generated_active_v390())return 0;
    list->draining=1;
    for(size_t i=list->count;i>0;--i) {
        const ShytDtorV423 entry=list->entries[i-1];
        if(!entry.fn || (dso && entry.dso!=dso))continue;
        list->entries[i-1].fn=0;
        if(!invoke(context,entry)) {
            list->draining=0;
            list->failed=1;
            return 0;
        }
    }
    size_t n=0;
    for(size_t i=0;i<list->count;++i)
        if(list->entries[i].fn)list->entries[n++]=list->entries[i];
    list->count=n;
    list->draining=0;
    return 1;
}
#endif
