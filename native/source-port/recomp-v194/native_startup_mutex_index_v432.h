/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_MUTEX_INDEX_V432_H
#define SHYT_STARTUP_MUTEX_INDEX_V432_H
#include "native_startup_mutex_routes_v416.h"
typedef struct {
    const ShytMutexRouteV416 *rows;
    size_t count, objects;
} ShytMutexIndexV432;

/* Validate once. The startup controller retains immutable rows sorted
 * by (scope, continuation) for the lifetime of this index. Scope is
 * selected by the controller, not by a guest register. */
static inline int shyt_mutex_index_init_v432(ShytMutexIndexV432 *index,
    const ShytMutexRouteV416 *rows,size_t count,size_t objects) {
    if(!index || index->rows || index->count || index->objects ||
       !rows || !count || count>256 || !objects || objects>64)return 0;
    for(size_t i=0;i<count;++i) {
        const ShytMutexRouteV416 r=rows[i];
        if(!r.scope || r.object>=objects || !r.site.target || !r.site.next ||
           r.site.target==r.site.next || (unsigned)r.site.op>SHYT_MUTEX_ATTR_DESTROY)
            return 0;
        if(i && (rows[i-1].scope>r.scope ||
           (rows[i-1].scope==r.scope && rows[i-1].site.next>=r.site.next)))return 0;
    }
    index->rows=rows;index->count=count;index->objects=objects;
    return 1;
}
static inline int shyt_mutex_index_call_v432(const ShytMutexIndexV432 *index,
    ShytStartupMutexStateV413 *objects,size_t count,uint32_t scope,
    BbCpu *expected,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!index || !index->rows || !index->count || index->count>256 ||
       !objects || !count || count>64 || index->objects!=count || !scope)return 0;
    size_t lo=0,hi=index->count;
    while(lo<hi) {
        const size_t mid=lo+(hi-lo)/2;
        const ShytMutexRouteV416 r=index->rows[mid];
        if(r.scope<scope || (r.scope==scope && r.site.next<next))lo=mid+1;
        else hi=mid;
    }
    if(lo==index->count)return 0;
    const ShytMutexRouteV416 *r=&index->rows[lo];
    return r->scope==scope && r->site.next==next && r->object<count &&
        shyt_mutex_call_v413(&objects[r->object],&r->site,expected,cpu,target,next);
}
#endif
