/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_STRING_ROUTES_V430_H
#define SHYT_STARTUP_STRING_ROUTES_V430_H
#include "native_startup_string_v415.h"
enum { SHYT_STRING_ROUTES_MAX_V430=1024 };
typedef struct { const ShytStrlenSiteV415 *rows; size_t count; } ShytStringRoutesV430;
/* Trusted immutable rows sorted by continuation, then by range start.
 * One service target per continuation. Windows cannot overlap or join
 * into a larger implicit string; the selected row owns the full scan. */
static inline int shyt_string_routes_init_v430(ShytStringRoutesV430 *plan,
    const ShytStrlenSiteV415 *rows,size_t count) {
    if(!plan || plan->rows || plan->count || !rows || !count || count>SHYT_STRING_ROUTES_MAX_V430)return 0;
    for(size_t i=0;i<count;++i){
        const ShytStrlenSiteV415 s=rows[i];
        if(!s.target || !s.next || s.target==s.next || !s.start || s.start>=s.end || !s.max_bytes || s.max_bytes>4096)return 0;
        if(i && (rows[i-1].next>s.next || (rows[i-1].next==s.next &&
            (rows[i-1].target!=s.target || rows[i-1].end>s.start))))return 0;
    }
    plan->rows=rows;plan->count=count;return 1;
}
static inline int shyt_string_route_v430(const ShytStringRoutesV430 *plan,
    ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!plan || !plan->rows || !plan->count || plan->count>SHYT_STRING_ROUTES_MAX_V430 || !cpu || cpu!=expected)return 0;
    const uint64_t addr=cpu->r[7];size_t lo=0,hi=plan->count;
    while(lo<hi){
        const size_t mid=lo+(hi-lo)/2;
        const ShytStrlenSiteV415 s=plan->rows[mid];
        if(s.next<next || (s.next==next && s.start<=addr))lo=mid+1;
        else hi=mid;
    }
    return lo && shyt_strlen_call_v415(owner,&plan->rows[lo-1],expected,cpu,target,next);
}
#endif
