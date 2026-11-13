/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_DISPATCH_V435_H
#define SHYT_STARTUP_DISPATCH_V435_H
#include "native_startup_ctor_plan_v427.h"
#include "native_startup_edges_v426.h"

typedef struct { uint32_t scope; ShytStartupEdgeV418 edge; } ShytScopedCallV435;
typedef struct { const RcFunction *row; } ShytBoundCallV435;
typedef struct {
    const ShytScopedCallV435 *routes;
    const ShytBoundCallV435 *bindings;
    size_t count;
    ShytNativeOsVmV388 *owner;
    BbCpu *cpu;
    uint64_t stack_lo, stack_hi;
    int terminal;
    const RcFunction *registry;
    size_t registry_count;
} ShytStartupDispatchV435;

static inline const RcFunction *shyt_lookup_call_row_v435(
    const RcFunction *table, size_t count, uint64_t id) {
    size_t lo=0,hi=count;
    while(lo<hi) {
        size_t m=lo+(hi-lo)/2;
        if(table[m].offset<id)lo=m+1; else hi=m;
    }
    return lo<count && table[lo].offset==id ? table+lo : NULL;
}
static inline int shyt_call_route_less_v435(ShytScopedCallV435 a, ShytScopedCallV435 b) {
    return a.scope<b.scope || (a.scope==b.scope &&
        (a.edge.next<b.edge.next || (a.edge.next==b.edge.next && a.edge.target<b.edge.target)));
}

/* Zero-init the controller. The host retains disjoint arrays, frozen after
 * preflight. No writes to the output bindings until every route validates.
 * Scope is the host's current constructor ordinal, not a guest argument.
 * Use only on the pinned replay thread. Discard on V393 nonlocal recovery. */
static inline int shyt_startup_dispatch_init_v435(ShytStartupDispatchV435 *state,
    ShytNativeOsVmV388 *owner,BbCpu *cpu,uint64_t stack_lo,uint64_t stack_hi,
    const ShytScopedCallV435 *routes,size_t count,const RcFunction *table,size_t table_count,
    ShytBoundCallV435 *bindings,size_t capacity) {
    if(!state || state->routes || state->bindings || state->count || state->owner ||
       state->cpu || state->registry || state->registry_count || state->terminal || !owner || !cpu || stack_hi<=stack_lo ||
       stack_hi-stack_lo<8 || !routes || !bindings || !count || count>capacity ||
       count>SHYT_STARTUP_EDGES_MAX_V426 || !table || !table_count ||
       table_count>SHYT_CTOR_REG_LIMIT_V427)return 0;
    for(size_t i=0;i<table_count;++i)
        if(!table[i].fn || (i && table[i-1].offset>=table[i].offset))return 0;
    for(size_t i=0;i<count;++i) {
        ShytScopedCallV435 r=routes[i];
        if(!r.scope || r.scope>SHYT_CTOR_LIMIT_V427 || !r.edge.target ||
           !r.edge.next || r.edge.target==r.edge.next ||
           (i && !shyt_call_route_less_v435(routes[i-1],r)) ||
           !shyt_lookup_call_row_v435(table,table_count,r.edge.target))return 0;
    }
    for(size_t i=0;i<count;++i)
        bindings[i].row=shyt_lookup_call_row_v435(table,table_count,routes[i].edge.target);
    *state=(ShytStartupDispatchV435){routes,bindings,count,owner,cpu,stack_lo,stack_hi,0,table,table_count};
    return 1;
}

/* Both DENIED and BAD_RETURN must stop a strict RcApi callback; never
 * hand either result to an interpreter. BAD_RETURN additionally poisons
 * this controller because the callee may already have changed state. */
static inline enum ShytStartupCallV418 shyt_startup_dispatch_v435(
    ShytStartupDispatchV435 *state,BbCpu *cpu,uint32_t scope,uint64_t target,uint64_t next) {
    if(!state || !state->routes || !state->bindings || !state->count ||
       state->count>SHYT_STARTUP_EDGES_MAX_V426 || !cpu || cpu!=state->cpu)
        return SHYT_STARTUP_DENIED;
    if(state->terminal)return SHYT_STARTUP_BAD_RETURN;
    const ShytScopedCallV435 key={scope,{target,next}};
    size_t lo=0,hi=state->count;
    while(lo<hi) {
        size_t m=lo+(hi-lo)/2;
        if(shyt_call_route_less_v435(state->routes[m],key))lo=m+1; else hi=m;
    }
    if(lo==state->count || shyt_call_route_less_v435(key,state->routes[lo]))
        return SHYT_STARTUP_DENIED;
    enum ShytStartupCallV418 result=shyt_startup_call_v418(state->owner,state->cpu,cpu,
        state->bindings[lo].row,1,&state->routes[lo].edge,target,next,state->stack_lo,state->stack_hi);
    if(result==SHYT_STARTUP_BAD_RETURN)state->terminal=1;
    return state->terminal ? SHYT_STARTUP_BAD_RETURN : result;
}
#endif
