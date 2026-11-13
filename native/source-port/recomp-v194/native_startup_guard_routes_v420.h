/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_GUARD_ROUTES_V420_H
#define SHYT_STARTUP_GUARD_ROUTES_V420_H
#include "native_static_guard_import_v413.h"

enum { SHYT_GUARD_MAX_ROUTES_V420=65536 };
typedef struct {
    const ShytGuardSiteV413 *rows;
    size_t count;
} ShytGuardRoutesV420;

/* Single startup controller. Keep rows immutable and alive. Sort by
 * continuation then guard address. One continuation has one service,
 * but its exact allowlist may contain more than one guard address. */
static inline int shyt_guard_routes_init_v420(ShytGuardRoutesV420 *routes,
    const ShytGuardSiteV413 *rows,size_t count) {
    if(!routes || routes->rows || routes->count || !rows ||
       !count || count>SHYT_GUARD_MAX_ROUTES_V420)return 0;
    for(size_t i=0;i<count;++i) {
        const ShytGuardSiteV413 *s=&rows[i];
        if(!s->target || !s->next || s->target==s->next ||
           !s->guard || (s->guard&7u) || s->guard>UINT64_MAX-8u ||
           (unsigned)s->action>SHYT_GUARD_ABORT)return 0;
        if(i) {
            const ShytGuardSiteV413 *p=&rows[i-1];
            if(p->next>s->next || (p->next==s->next &&
               (p->guard>=s->guard || p->target!=s->target || p->action!=s->action)))
                return 0;
        }
    }
    routes->rows=rows;
    routes->count=count;
    return 1;
}
static inline int shyt_guard_dispatch_v420(const ShytGuardRoutesV420 *routes,
    ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!routes || !routes->rows || !routes->count ||
       routes->count>SHYT_GUARD_MAX_ROUTES_V420 || !cpu || cpu!=expected)return 0;
    const uint64_t guard=cpu->r[7];
    size_t lo=0,hi=routes->count;
    while(lo<hi) {
        const size_t mid=lo+(hi-lo)/2;
        const ShytGuardSiteV413 *s=&routes->rows[mid];
        if(s->next<next || (s->next==next && s->guard<guard))lo=mid+1;
        else hi=mid;
    }
    if(lo==routes->count)return 0;
    return shyt_guard_call_v413(owner,&routes->rows[lo],expected,cpu,target,next);
}
#endif
