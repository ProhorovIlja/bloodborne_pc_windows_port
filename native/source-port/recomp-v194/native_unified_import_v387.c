/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_unified_import_v387.h"
#include "native_math_shim_v222.h"
#include <stdint.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

static const char *const k_math_v387[23]={
    "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
    "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
    "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
};
static _Atomic(ShytUnifiedImportV387 *) active_v387=ATOMIC_VAR_INIT(NULL);
static int math_op_v387(const char *name) {
    if (!name)return -1;
    for(int i=0;i<23;i++)if(strcmp(name,k_math_v387[i])==0)return i;
    return -1;
}
static int exact_stack_region_v387(ShytNativeVmV386 *vm,
                                  const ShytNativeStackV383 *stack) {
    if(!vm || !vm->sealed || !vm->region_count ||
       !stack || stack->ready!=1 || !stack->backing ||
       !stack->word_count) return 0;
    for(size_t i=0;i<vm->region_count;i++) {
        const ShytNativeRegionV386 *r=&vm->regions[i];
        if(r->guest_base==stack->guest_base &&
           r->words==stack->backing && r->word_count==stack->word_count &&
           (r->permissions&(SHYT_V386_READ|SHYT_V386_WRITE))==
                           (SHYT_V386_READ|SHYT_V386_WRITE))
            return 1;
    }
    return 0;
}
int shyt_native_boot_finalize_multiregion_v387(
    ShytNativeBootChainV384 *chain,ShytAotServicesV245 *services,
    const RcApi *strict,ShytNativeStackV383 *stack,
    ShytNativeVmV386 *vm,ShytStrictAotAttestV381 attest,void *ctx) {
    ShytNativeVmLeaseV386 lease={0};
    int ok=0;
    if(!exact_stack_region_v387(vm,stack) ||
       !shyt_native_boot_preflight_v384(services,strict,stack) ||
       !shyt_native_vm_pin_v386(vm,&lease)) return 0;
    ok=shyt_native_vm_probe_v386(
        &lease,stack->guest_base,8,SHYT_V386_READ|SHYT_V386_WRITE);
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    if(!ok)return 0;
    /* The V382 dispatcher is published ONLY once with V386 writer.
     * Its strict base callbacks and exact hash attestation remain V384. */
    return shyt_native_boot_finalize_with_writer_v387(
        chain,services,strict,stack,shyt_native_vm_stack_write_v386,vm,
        attest,ctx);
}
int shyt_unified_import_prepare_v387(
    ShytUnifiedImportV387 *r,ShytAotServicesV245 *s,
    ShytNativeBootChainV384 *chain,ShytNativeVmV386 *vm,
    const ShytMathImportDesc *descs,size_t count) {
    ShytUnifiedImportV387 next={0};
    ShytNativeVmLeaseV386 lease={0};
    uint32_t seen=0;
    if(!r || r->ready || r->published || r->services || r->vm ||
       !s || !chain || !chain->published ||
       !chain->route.ready || !chain->route.published ||
       chain->route.stack_write!=shyt_native_vm_stack_write_v386 ||
       chain->route.stack_context!=vm ||
       !s->native_only_finalized_v384 || !s->published_api ||
       s->published_api!=&s->clock.api || !s->functions ||
       !s->function_count ||
       chain->proof.functions_attested!=s->function_count ||
       !chain->proof.no_guest_fallback_callbacks ||
       !vm || vm->sealed!=1 || !vm->region_count ||
       !descs || count!=23 || !s->math.original.call ||
       s->math.original.call==s->math.api.call ||
       !s->clock.api.call || s->clock.api.call==s->math.original.call ||
       !s->clock.api.tail || s->clock.api.tail!=s->math.original.tail ||
       s->clock.api.tail!=s->math.api.tail ||
       s->clock.targets.image_base!=s->math.table.image_base ||
       s->clock.targets.image_base!=s->clock.api.image_base ||
       !s->clock.targets.read_tsc_offset ||
       !s->clock.targets.get_tsc_frequency_offset ||
       s->clock.targets.read_tsc_offset>
           UINT64_MAX-s->clock.targets.image_base ||
       s->clock.targets.get_tsc_frequency_offset>
           UINT64_MAX-s->clock.targets.image_base ||
       atomic_load_explicit(&active_v387,memory_order_acquire) ||
       !shyt_native_vm_pin_v386(vm,&lease))return 0;
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    next.services=s;next.chain=chain;next.vm=vm;
    next.native_fallback=s->math.original.call; /* verified V382 only */
    next.clock_ticks=s->clock.targets.image_base+
                     s->clock.targets.read_tsc_offset;
    next.clock_frequency=s->clock.targets.image_base+
                         s->clock.targets.get_tsc_frequency_offset;
    if(next.clock_ticks==next.clock_frequency)return 0;
    for(size_t i=0;i<23;i++) {
        int op=math_op_v387(descs[i].name);
        uint64_t base=s->math.table.image_base;
        if(op<0 || (seen&(UINT32_C(1)<<(unsigned)op)) ||
           !descs[i].offset || descs[i].offset>UINT64_MAX-base ||
           descs[i].offset!=s->math.table.entries[i].offset ||
           s->math.table.entries[i].fn!=
               shyt_guest_math_v223_find(descs[i].name))return 0;
        next.math_targets[i]=base+descs[i].offset;
        next.math_opcodes[i]=(uint8_t)op;
        if(next.math_targets[i]==next.clock_ticks ||
           next.math_targets[i]==next.clock_frequency)return 0;
        seen|=UINT32_C(1)<<(unsigned)op;
    }
    if(seen!=(UINT32_C(1)<<23)-1)return 0;
    next.ready=1;
    *r=next;
    return 1;
}
static int perform_v387(ShytUnifiedImportV387 *r,BbCpu *cpu,
                         uint64_t next,int op) {
    ShytNativeVmLeaseV386 lease={0};
    uint64_t slot=0,out=0,clock_value=0;
    int exponent=0,writes_exponent=0;
    int is_double=0,is_float=0,is_clock=0;
    double d=0.0;float f=0.0f;
    if(!r || !cpu || !next || cpu->r[RSP]<8 ||
       !shyt_native_vm_pin_v386(r->vm,&lease))return 0;
    slot=cpu->r[RSP]-8;
    if(!shyt_native_vm_probe_v386(
            &lease,slot,8,SHYT_V386_WRITE))goto deny;
    if(op==14 || op==15) {
        out=cpu->r[RDI];
        /* No overflow, overlap, read-only, missing mapping or word
         * crossing accepted. All checks BEFORE math/guest stores. */
        if(out>UINT64_MAX-4 ||
           !(out+4<=slot || slot+8<=out) ||
           !shyt_native_vm_probe_v386(
               &lease,out,4,SHYT_V386_WRITE))goto deny;
        writes_exponent=1;
    }
    if(op==23 || op==24) {
        is_clock=1;
        if(op==23) {
            if(shyt_clock_ticks_v236(&r->services->clock.clock,
              UINT64_C(1600000000),&clock_value))goto deny;
        } else clock_value=UINT64_C(1600000000);
    }else {
        switch(op) {
        case 0:d=shyt_math_acos(cpu->v[0].fd[0]);is_double=1;break;
        case 1:f=shyt_math_acosf(cpu->v[0].f[0]);is_float=1;break;
        case 2:d=shyt_math_asin(cpu->v[0].fd[0]);is_double=1;break;
        case 3:f=shyt_math_asinf(cpu->v[0].f[0]);is_float=1;break;
        case 4:d=shyt_math_atan(cpu->v[0].fd[0]);is_double=1;break;
        case 5:d=shyt_math_atan2(cpu->v[0].fd[0],cpu->v[1].fd[0]);is_double=1;break;
        case 6:f=shyt_math_atan2f(cpu->v[0].f[0],cpu->v[1].f[0]);is_float=1;break;
        case 7:f=shyt_math_atanf(cpu->v[0].f[0]);is_float=1;break;
        case 8:d=shyt_math_exp(cpu->v[0].fd[0]);is_double=1;break;
        case 9:d=shyt_math_exp2(cpu->v[0].fd[0]);is_double=1;break;
        case 10:f=shyt_math_exp2f(cpu->v[0].f[0]);is_float=1;break;
        case 11:f=shyt_math_expf(cpu->v[0].f[0]);is_float=1;break;
        case 12:d=shyt_math_fmod(cpu->v[0].fd[0],cpu->v[1].fd[0]);is_double=1;break;
        case 13:f=shyt_math_fmodf(cpu->v[0].f[0],cpu->v[1].f[0]);is_float=1;break;
        case 14:d=shyt_math_frexp(cpu->v[0].fd[0],&exponent);is_double=1;break;
        case 15:f=shyt_math_frexpf(cpu->v[0].f[0],&exponent);is_float=1;break;
        case 16:d=shyt_math_ldexp(cpu->v[0].fd[0],(int)cpu->r[RDI]);is_double=1;break;
        case 17:f=shyt_math_ldexpf(cpu->v[0].f[0],(int)cpu->r[RDI]);is_float=1;break;
        case 18:d=shyt_math_pow(cpu->v[0].fd[0],cpu->v[1].fd[0]);is_double=1;break;
        case 19:f=shyt_math_powf(cpu->v[0].f[0],cpu->v[1].f[0]);is_float=1;break;
        case 20:d=shyt_math_tan(cpu->v[0].fd[0]);is_double=1;break;
        case 21:f=shyt_math_tanf(cpu->v[0].f[0]);is_float=1;break;
        case 22:f=shyt_math_tanhf(cpu->v[0].f[0]);is_float=1;break;
        default:goto deny;
        }
    }
    /* V386 sealed map remains invariant under pin. Both destinations
     * have been validated; a failed returned write is a logic fault.
     * No general multi-address transaction isolation is claimed. */
    if(writes_exponent &&
       !shyt_native_vm_write_v386(
           &lease,out,4,(uint32_t)exponent))abort();
    if(!shyt_native_vm_write_v386(&lease,slot,8,next))abort();
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    if(is_double)cpu->v[0].fd[0]=d;
    if(is_float)cpu->v[0].f[0]=f;
    if(is_clock)cpu->r[RAX]=clock_value;
    cpu->rip=next;
    return 1;
deny:
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    return 0;
}
int shyt_unified_import_try_v387(
    ShytUnifiedImportV387 *r,BbCpu *cpu,uint64_t target,uint64_t next) {
    int op=-1;
    if(!r || r->ready!=1 || !r->vm)return -1;
    if(target==r->clock_ticks)op=23;
    else if(target==r->clock_frequency)op=24;
    else for(size_t i=0;i<23;i++)
        if(target==r->math_targets[i]){op=(int)r->math_opcodes[i];break;}
    if(op<0)return 0;
    return perform_v387(r,cpu,next,op)?1:-1;
}
static void import_call_v387(BbCpu *cpu,uint64_t target,uint64_t next) {
    ShytUnifiedImportV387 *r=atomic_load_explicit(
        &active_v387,memory_order_acquire);
    if(!r || !r->ready || !r->published)abort();
    int handled=shyt_unified_import_try_v387(r,cpu,target,next);
    if(handled==1)return;
    if(handled<0)abort();
    r->native_fallback(cpu,target,next); /* V382 native AOT or ABORT */
}
int shyt_unified_import_publish_v387(ShytUnifiedImportV387 *r) {
    ShytNativeVmLeaseV386 lease={0};
    ShytUnifiedImportV387 *expected=NULL;
    if(!r || r->ready!=1 || r->published ||
       !r->services || !r->chain || !r->vm || !r->native_fallback ||
       !r->services->native_only_finalized_v384 ||
       r->services->published_api!=&r->services->clock.api ||
       r->services->clock.api.call==import_call_v387 ||
       r->chain->route.stack_context!=r->vm ||
       r->chain->route.stack_write!=shyt_native_vm_stack_write_v386 ||
       !shyt_native_vm_pin_v386(r->vm,&lease))return 0;
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    if(!atomic_compare_exchange_strong_explicit(
          &active_v387,&expected,r,memory_order_release,
          memory_order_acquire))return 0;
    /* Process-lifetime single-threaded publication only. */
    r->published=1;
    r->services->clock.api.call=import_call_v387;
    return 1;
}
