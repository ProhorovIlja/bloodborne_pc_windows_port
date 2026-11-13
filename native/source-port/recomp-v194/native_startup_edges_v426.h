/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_EDGES_V426_H
#define SHYT_STARTUP_EDGES_V426_H
#include "native_startup_call_v418.h"
enum { SHYT_STARTUP_EDGES_MAX_V426=65536 };
typedef struct { const ShytStartupEdgeV418 *edges; size_t n; } ShytStartupEdgesV426;
/* The controller owns immutable arrays for the replay lifetime. Registry
 * must already have been validated and sorted. No general CFI claim:
 * the emitter provides a continuation, not a trustworthy source PC. */
static inline int shyt_startup_edges_init_v426(ShytStartupEdgesV426 *plan,
    const ShytStartupEdgeV418 *edges,size_t n,const RcFunction *table,size_t count) {
    if(!plan || plan->edges || plan->n || !edges || !n || n>SHYT_STARTUP_EDGES_MAX_V426 ||
       !table || !count)return 0;
    for(size_t i=0;i<n;++i) {
        const ShytStartupEdgeV418 e=edges[i];
        if(!e.target || !e.next || e.target==e.next || !shyt_startup_find_v418(table,count,e.target))return 0;
        if(i && (edges[i-1].next>e.next || (edges[i-1].next==e.next && edges[i-1].target>=e.target)))return 0;
    }
    plan->edges=edges;plan->n=n;
    return 1;
}
static inline const ShytStartupEdgeV418 *shyt_startup_edge_v426(const ShytStartupEdgesV426 *plan,
    uint64_t target,uint64_t next) {
    if(!plan || !plan->edges || !plan->n || plan->n>SHYT_STARTUP_EDGES_MAX_V426)return NULL;
    size_t lo=0,hi=plan->n;
    while(lo<hi) {
        const size_t mid=lo+(hi-lo)/2;
        const ShytStartupEdgeV418 e=plan->edges[mid];
        if(e.next<next || (e.next==next && e.target<target))lo=mid+1;
        else hi=mid;
    }
    return lo<plan->n && plan->edges[lo].next==next && plan->edges[lo].target==target
        ? &plan->edges[lo] : NULL;
}
#endif
