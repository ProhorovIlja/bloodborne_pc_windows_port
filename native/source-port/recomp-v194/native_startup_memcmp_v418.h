/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_MEMCMP_V418_H
#define SHYT_STARTUP_MEMCMP_V418_H
#include "native_startup_call_v418.h"
typedef struct {
    ShytStartupEdgeV418 edge;
    uint64_t lo,hi;
    size_t max_bytes;
} ShytMemcmpSiteV418;
/* Both inputs must lie within the audited window. This subset permits
 * bounded byte comparison, not arbitrary native-pointer access. */
static inline int shyt_memcmp_v418(ShytNativeOsVmV388 *owner,BbCpu *expected,BbCpu *cpu,
    const ShytMemcmpSiteV418 *s,uint64_t target,uint64_t next) {
    if(!owner || !cpu || cpu!=expected || !s || !target || !next || target==next ||
       s->edge.target!=target || s->edge.next!=next || s->lo>=s->hi ||
       !s->max_bytes || s->max_bytes>4096 || shyt_generated_owner_v392()!=owner ||
       shyt_generated_recovery_depth_v393()!=1u)return 0;
    const uint64_t a=cpu->r[7], b=cpu->r[6], n=cpu->r[2];
    if(n>s->max_bytes || (n && (a<s->lo || b<s->lo || a>=s->hi || b>=s->hi ||
       n>s->hi-a || n>s->hi-b || !shyt_generated_probe_range_v412(a,(size_t)n,SHYT_V386_READ) ||
       !shyt_generated_probe_range_v412(b,(size_t)n,SHYT_V386_READ))))return 0;
    int diff=0;
    for(uint64_t i=0;i<n;++i){
        uint64_t x,y;
        if(!shyt_generated_try_load_v390(a+i,1,&x) || !shyt_generated_try_load_v390(b+i,1,&y))return 0;
        if(x!=y){diff=(int)x-(int)y;break;}
    }
    cpu->r[0]=(uint32_t)diff;
    cpu->rip=next;
    return 1;
}
#endif
