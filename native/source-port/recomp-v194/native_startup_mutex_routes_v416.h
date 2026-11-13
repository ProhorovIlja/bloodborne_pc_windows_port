/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_MUTEX_ROUTES_V416_H
#define SHYT_STARTUP_MUTEX_ROUTES_V416_H
#include "native_startup_mutex_import_v413.h"

/* The startup controller, not the guest, selects a nonzero scope for
 * the active constructor. Identical machine callsites can be reached
 * with different stack layouts in different constructors. A scope
 * never grants permission to select an object by an unchecked RDI.
 * Tables and state slots remain stable under a single controller. */
typedef struct {
    uint32_t scope;
    size_t object;
    ShytStartupMutexSiteV413 site;
} ShytMutexRouteV416;

static inline int shyt_mutex_routes_valid_v416(const ShytMutexRouteV416 *routes,
    size_t n,size_t objects) {
    if(!routes || !n || n>256 || !objects || objects>64)return 0;
    for(size_t i=0;i<n;++i) {
        const ShytMutexRouteV416 *r=&routes[i];
        if(!r->scope || r->object>=objects || !r->site.target || !r->site.next ||
           r->site.target==r->site.next ||
           (unsigned)r->site.op>SHYT_MUTEX_ATTR_DESTROY)return 0;
        for(size_t j=0;j<i;++j)
            if(routes[j].scope==r->scope && routes[j].site.next==r->site.next)
                return 0;
    }
    return 1;
}
/* Invoke only with a prevalidated immutable plan. Reject any unmatched
 * scope, continuation or target; no guest state is changed on denial.
 * The existing import adapter separately checks owner, CPU, argument
 * slots and the native mutex lifecycle. */
static inline int shyt_mutex_dispatch_v416(const ShytMutexRouteV416 *routes,
    size_t n,ShytStartupMutexStateV413 *objects,size_t count,uint32_t scope,
    BbCpu *expected,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!routes || !objects || !scope || !n || n>256 || !count || count>64)return 0;
    const ShytMutexRouteV416 *match=NULL;
    for(size_t i=0;i<n;++i) {
        if(routes[i].scope!=scope || routes[i].site.next!=next)continue;
        if(match)return 0;
        match=&routes[i];
    }
    return match && match->object<count &&
           shyt_mutex_call_v413(&objects[match->object],&match->site,
                               expected,cpu,target,next);
}
#endif
