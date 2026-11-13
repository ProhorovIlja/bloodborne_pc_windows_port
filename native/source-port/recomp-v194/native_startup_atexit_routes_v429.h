/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_ATEXIT_ROUTES_V429_H
#define SHYT_STARTUP_ATEXIT_ROUTES_V429_H
#include "native_startup_atexit_tail_v425.h"

enum { SHYT_ATEXIT_TAIL_MAX_V429=256 };
typedef struct { const ShytAtexitTailSiteV425 *rows; size_t count; } ShytAtexitRoutesV429;

/* One approved tail registration per constructor in this subset.
 * Controller owns immutable rows and the prevalidated sorted registry.
 * This is not a general RcApi.tail router or proof of origin PC. */
static inline int shyt_atexit_routes_init_v429(ShytAtexitRoutesV429 *plan,
    const ShytAtexitTailSiteV425 *rows,size_t n,const RcFunction *table,size_t count) {
    if(!plan || plan->rows || plan->count || !rows || !n ||
       n>SHYT_ATEXIT_TAIL_MAX_V429 || !table || !count)return 0;
    for(size_t i=0;i<n;++i) {
        const ShytAtexitTailSiteV425 *s=&rows[i];
        const ShytStartupEdgeV418 e=s->registration.edge;
        const ShytDtorV423 t=s->registration.tuple;
        if(!s->scope || (i && rows[i-1].scope>=s->scope) ||
           !e.target || !e.next || e.target==e.next || !t.fn || !t.object || !t.dso ||
           !shyt_startup_find_v418(table,count,t.fn))return 0;
    }
    plan->rows=rows;
    plan->count=n;
    return 1;
}
static inline int shyt_atexit_route_tail_v429(const ShytAtexitRoutesV429 *plan,
    ShytAtexitV423 *list,ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,
    const RcFunction *table,size_t count,uint32_t scope,uint64_t stack_lo,uint64_t stack_hi) {
    if(!plan || !plan->rows || !plan->count || plan->count>SHYT_ATEXIT_TAIL_MAX_V429 || !scope)return 0;
    size_t lo=0,hi=plan->count;
    while(lo<hi) {
        const size_t mid=lo+(hi-lo)/2;
        if(plan->rows[mid].scope<scope)lo=mid+1;
        else hi=mid;
    }
    return lo<plan->count && plan->rows[lo].scope==scope &&
        shyt_atexit_tail_v425(list,owner,expected,cpu,table,count,&plan->rows[lo],scope,stack_lo,stack_hi);
}
#endif
