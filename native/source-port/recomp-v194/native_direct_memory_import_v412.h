/* SPDX-License-Identifier: GPL-2.0-or-later
 * Single-controller startup-only direct-memory aperture. Every execution
 * pin that can access it MUST install the same guard before generated code.
 * Not a general PS4 MMU: direct V388 calls and other threads bypass the guard.
 */
#ifndef SHYT_DM_IMPORT_V412_H
#define SHYT_DM_IMPORT_V412_H
#include "full_cpu_abi_v194.h"
#include "native_direct_memory_v411.h"
#include "native_host_recovery_v393.h"

typedef enum { SHYT_DM_SIZE,SHYT_DM_ALLOC,SHYT_DM_MAP,SHYT_DM_FREE } ShytDmService;
typedef struct { uint64_t target,next; ShytDmService service; } ShytDmSite;
typedef struct {
    ShytNativeOsVmV388 *owner;
    ShytDmPool pool;
    uint64_t base, mapped, length;
    BbCpu *cpu;
    const ShytDmSite *sites;
    size_t count;
} ShytDmImport;
/* Low 32-bit Orbis status values, with x86 EAX zero extension. */
#define SHYT_DM_EAGAIN UINT64_C(0x80020023)
#define SHYT_DM_EFAULT UINT64_C(0x8002000e)
#define SHYT_DM_EINVAL UINT64_C(0x80020016)
#define SHYT_DM_ENOTSUP UINT64_C(0x8002002d)

static inline int shyt_dm_gate_v412(void *v,uint64_t addr,size_t bytes,unsigned perm) {
    ShytDmImport *s=v;
    if(addr>=s->base+s->pool.limit || addr+bytes<=s->base)return 1;
    return !(perm&SHYT_V386_EXECUTE) && s->length && addr>=s->mapped &&
           addr-s->mapped<s->length && bytes<=s->length-(addr-s->mapped);
}

static inline int shyt_dm_begin_pinned_v412(ShytDmImport *s,BbCpu *cpu,const ShytDmSite *sites,size_t count) {
    if(!sites || !count || count>32)return 0;
    for(size_t i=0;i<count;++i) {
        if(!sites[i].target || !sites[i].next || sites[i].target==sites[i].next ||
           (unsigned)sites[i].service>SHYT_DM_FREE)return 0;
        for(size_t j=0;j<i;++j)if(sites[j].next==sites[i].next)return 0;
    }
    return s && cpu && !s->cpu && s->owner &&
           shyt_generated_owner_v392()==s->owner &&
           shyt_generated_recovery_depth_v393()==1u &&
           s->base && !(s->base%SHYT_DM_PAGE) && s->pool.limit &&
           s->pool.limit<=SIZE_MAX && s->base<=UINT64_MAX-s->pool.limit &&
           shyt_generated_probe_range_v412(s->base,(size_t)s->pool.limit,
                                           SHYT_V386_READ|SHYT_V386_WRITE) &&
           shyt_generated_filter_v412(shyt_dm_gate_v412,s) &&
           (s->cpu=cpu,s->sites=sites,s->count=count,1);
}
/* Called only after the V393 wrapper returns (including cooperative escape). */
typedef struct {
    ShytDmImport *state;
    BbCpu *cpu;
    const ShytDmSite *sites;
    size_t count;
} ShytDmStartV412;
static inline int shyt_dm_preflight_v412(const BbCpu *cpu,void *ctx) {
    ShytDmStartV412 *start=ctx;
    return start->cpu==cpu &&
           shyt_dm_begin_pinned_v412(start->state,start->cpu,start->sites,start->count);
}
/* Only public entry for this aperture. Owns a fresh pin; borrowed pins
 * would otherwise retain the filter on return. No generic V390 entry
 * into this owner is permitted while startup aperture policy is needed. */
static inline int shyt_dm_run_v412(ShytDmImport *s,ShytGeneratedFnV392 fn,
    BbCpu *cpu,const ShytDmSite *sites,size_t count,int *code) {
    if(!s || !s->owner || s->cpu || !fn || !cpu || shyt_generated_active_v390() ||
       shyt_generated_recovery_depth_v393())return SHYT_V393_DENIED;
    ShytDmStartV412 start={s,cpu,sites,count};
    const int result=shyt_generated_call_recoverable_v393(s->owner,fn,cpu,
        shyt_dm_preflight_v412,&start,code);
    s->cpu=NULL;
    s->sites=NULL;
    s->count=0;
    return result;
}
static inline uint64_t shyt_dm_error_v412(enum ShytDmResult result) {
    switch(result) {
    case SHYT_DM_OK:return 0;
    case SHYT_DM_INVALID:return SHYT_DM_EINVAL;
    case SHYT_DM_NO_SPACE:return SHYT_DM_EAGAIN;
    default:return SHYT_DM_ENOTSUP;
    }
}
static inline int shyt_dm_output_v412(ShytDmImport *s,uint64_t addr,uint64_t rsp,unsigned perm) {
    return !(addr&7u) && addr<=UINT64_MAX-8u && rsp<=UINT64_MAX-8u &&
           (addr>=rsp+8u || addr+8u<=rsp) &&
           (addr>=s->base+s->pool.limit || addr+8u<=s->base) &&
           shyt_generated_try_probe_v390(addr,8,perm);
}
/* Caller supplies an immutable attested site selected by the enclosing
 * route. Wrong target/next/CPU returns 0 with no effects, not a fallback. */
static inline int shyt_dm_call_v412(ShytDmImport *s,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!s || !cpu || s->cpu!=cpu || !s->sites ||
       shyt_generated_owner_v392()!=s->owner ||
       shyt_generated_recovery_depth_v393()!=1u)return 0;
    enum { A=0,C=1,D=2,SP=4,SI=6,DI=7,R8_=8,R9_=9 };
    uint64_t result=SHYT_DM_EINVAL, off=0, hint=0;
    const uint64_t *r=cpu->r;
    size_t i=0;
    while(i<s->count && (s->sites[i].target!=target || s->sites[i].next!=next))++i;
    if(i==s->count)return 0;
    switch(s->sites[i].service) {
    case SHYT_DM_SIZE: result=s->pool.limit; break;
    case SHYT_DM_ALLOC:
        if(!shyt_dm_output_v412(s,r[R9_],r[SP],SHYT_V386_WRITE)) {
            result=SHYT_DM_EFAULT;
        } else if(r[DI]<=INT64_MAX && r[SI]<=INT64_MAX && (uint32_t)r[R8_]<=10) {
            result=shyt_dm_error_v412(shyt_dm_allocate(&s->pool,(int64_t)r[DI],
                (int64_t)r[SI],r[D],r[C],(int)(uint32_t)r[R8_],&off));
            if(!result && !shyt_generated_try_store_v390(r[R9_],8,off)) {
                if(shyt_dm_release(&s->pool,off,r[D])!=SHYT_DM_OK)return 0;
                result=SHYT_DM_EFAULT;
            }
        }
        break;
    case SHYT_DM_MAP: {
        const uint64_t align=r[R9_]?r[R9_]:SHYT_DM_PAGE;
        off=r[R8_];
        if(!shyt_dm_output_v412(s,r[DI],r[SP],SHYT_V386_READ|SHYT_V386_WRITE) ||
           !shyt_generated_try_load_v390(r[DI],8,&hint)) {
            result=SHYT_DM_EFAULT; break;
        }
        if((uint32_t)r[D]!=3 || (uint32_t)r[C] || hint || s->length ||
           align%SHYT_DM_PAGE || !r[SI] ||
           shyt_dm_find(&s->pool,off,r[SI])==s->pool.count ||
           (s->base+off)%align) {
            result=SHYT_DM_ENOTSUP; break;
        }
        s->mapped=s->base+off;
        s->length=r[SI];
        if(!shyt_generated_zero_v412(s->mapped,(size_t)s->length) ||
           !shyt_generated_try_store_v390(r[DI],8,s->mapped)) {
            s->length=0; s->mapped=0; result=SHYT_DM_EFAULT;
        } else result=0;
        break;
    }
    case SHYT_DM_FREE:
        result=shyt_dm_error_v412(shyt_dm_release(&s->pool,r[DI],r[SI]));
        if(!result && s->length && r[DI]==s->mapped-s->base && r[SI]==s->length)
            s->length=s->mapped=0;
        break;
    }
    cpu->r[A]=result;
    cpu->rip=next;
    return 1;
}
#endif
