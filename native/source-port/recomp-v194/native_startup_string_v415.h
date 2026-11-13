/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_STRING_V415_H
#define SHYT_STARTUP_STRING_V415_H
#include "full_cpu_abi_v194.h"
#include "native_host_recovery_v393.h"
enum { SHYT_STARTUP_STRING_MAX_V415=4096 };
/* Startup-only strlen. Read exactly through the terminator and never
 * beyond it. Caller selects a fixed audited target, continuation and
 * admissible logical address interval, not a native host pointer. */
typedef struct {
    uint64_t target, next, start, end;
    size_t max_bytes;
} ShytStrlenSiteV415;
static inline int shyt_strlen_call_v415(ShytNativeOsVmV388 *owner,
    const ShytStrlenSiteV415 *site,BbCpu *expected,BbCpu *cpu,
    uint64_t target,uint64_t next) {
    if(!owner || !site || !cpu || cpu!=expected || !target || !next ||
       target==next || target!=site->target || next!=site->next ||
       !site->start || site->end<=site->start || !site->max_bytes ||
       site->max_bytes>SHYT_STARTUP_STRING_MAX_V415 ||
       shyt_generated_owner_v392()!=owner ||
       shyt_generated_recovery_depth_v393()!=1u)return 0;
    uint64_t p=cpu->r[7];
    if(p<site->start || p>=site->end)return 0;
    for(size_t i=0;i<site->max_bytes && p<site->end;++i,++p) {
        uint64_t byte;
        if(!shyt_generated_try_load_v390(p,1,&byte))return 0;
        if(!byte) {
            cpu->r[0]=i;
            cpu->rip=next;
            return 1;
        }
    }
    return 0;
}
#endif
