/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_unified_import_v385.h"
#include "native_math_shim_v222.h"
#include <stdint.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
/* Match pinned V224 descriptor names, without invoking V223 raw-pointer
 * guest wrappers. All methods here use one V385 mapping. */
static const char *const math_names_v385[23]={
    "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
    "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
    "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
};
static _Atomic(ShytUnifiedImportV385 *) active_v385=ATOMIC_VAR_INIT(NULL);
static int math_opcode(const char *name) {
    if (!name) return -1;
    for(int i=0;i<23;i++)
        if (strcmp(name,math_names_v385[i])==0)return i;
    return -1;
}
int shyt_unified_import_prepare_v385(
    ShytUnifiedImportV385 *r,ShytAotServicesV245 *s,
    ShytNativeBootChainV384 *chain,ShytGuestVmV385 *vm,
    const ShytMathImportDesc *descs,size_t count) {
    ShytUnifiedImportV385 candidate={0};
    uint32_t seen=0;
    if (!r || r->ready || r->published || r->services || r->vm ||
        !s || !chain || !chain->published ||
        !chain->route.ready || !chain->route.published ||
        !s->native_only_finalized_v384 ||
        !s->published_api || s->published_api!=&s->clock.api ||
        !s->functions || !s->function_count ||
        chain->proof.functions_attested!=s->function_count ||
        !chain->proof.no_guest_fallback_callbacks ||
        !vm || !vm->ready || !vm->stack || vm->stack->ready!=1 ||
        chain->route.stack_context!=vm->stack ||
        !descs || count!=23 || !s->math.original.call ||
        s->math.original.call==s->math.api.call ||
        !s->clock.api.call || s->clock.api.call==s->math.original.call ||
        !s->clock.api.tail || s->clock.api.tail==s->math.original.tail ||
        s->clock.targets.image_base!=s->math.table.image_base ||
        s->clock.targets.image_base!=s->clock.api.image_base ||
        !s->clock.targets.read_tsc_offset ||
        !s->clock.targets.get_tsc_frequency_offset ||
        s->clock.targets.read_tsc_offset>
           UINT64_MAX-s->clock.targets.image_base ||
        s->clock.targets.get_tsc_frequency_offset>
           UINT64_MAX-s->clock.targets.image_base ||
        atomic_load_explicit(&active_v385,memory_order_acquire)) return 0;
    candidate.services=s;candidate.chain=chain;candidate.vm=vm;
    candidate.native_fallback=s->math.original.call;
    candidate.clock_ticks=s->clock.targets.image_base+
                           s->clock.targets.read_tsc_offset;
    candidate.clock_frequency=s->clock.targets.image_base+
                           s->clock.targets.get_tsc_frequency_offset;
    if(candidate.clock_ticks==candidate.clock_frequency)return 0;
    for(size_t i=0;i<23;i++) {
        int opcode=math_opcode(descs[i].name);
        uint64_t base=s->math.table.image_base;
        if(opcode<0 || (seen&(UINT32_C(1)<<(unsigned)opcode)) ||
           !descs[i].offset || descs[i].offset>UINT64_MAX-base ||
           descs[i].offset!=s->math.table.entries[i].offset ||
           s->math.table.entries[i].fn!=
              shyt_guest_math_v223_find(descs[i].name)) return 0;
        candidate.math_targets[i]=base+descs[i].offset;
        candidate.math_opcodes[i]=(uint8_t)opcode;
        if(candidate.math_targets[i]==candidate.clock_ticks ||
           candidate.math_targets[i]==candidate.clock_frequency) return 0;
        seen|=UINT32_C(1)<<(unsigned)opcode;
    }
    if(seen!=(UINT32_C(1)<<23)-1)return 0;
    candidate.ready=1;
    *r=candidate;
    return 1;
}
static int handle_import(ShytUnifiedImportV385 *r,BbCpu *cpu,
                         uint64_t target,uint64_t next,int opcode) {
    ShytGuestVmLeaseV385 lease={0};
    uint64_t slot,output_address=0,result_int=0;
    int have_out=0,exp=0;
    double result_d=0;
    float result_f=0;
    int is_double=0,is_float=0,is_clock=0;
    if(!r || !cpu || !next || cpu->r[RSP]<8 ||
       !shyt_guest_vm_pin_v385(r->vm,&lease))return 0;
    slot=cpu->r[RSP]-8;
    if(!shyt_guest_vm_probe_v385(&lease,slot,8))goto bad;
    if(opcode==23 || opcode==24) {
        is_clock=1;
        if(opcode==23) {
            if(shyt_clock_ticks_v236(&r->services->clock.clock,
                UINT64_C(1600000000),&result_int)) goto bad;
        } else result_int=UINT64_C(1600000000);
    }else {
        switch(opcode) {
        case 0: result_d=shyt_math_acos(cpu->v[0].fd[0]);is_double=1;break;
        case 1: result_f=shyt_math_acosf(cpu->v[0].f[0]);is_float=1;break;
        case 2: result_d=shyt_math_asin(cpu->v[0].fd[0]);is_double=1;break;
        case 3: result_f=shyt_math_asinf(cpu->v[0].f[0]);is_float=1;break;
        case 4: result_d=shyt_math_atan(cpu->v[0].fd[0]);is_double=1;break;
        case 5: result_d=shyt_math_atan2(cpu->v[0].fd[0],cpu->v[1].fd[0]);is_double=1;break;
        case 6: result_f=shyt_math_atan2f(cpu->v[0].f[0],cpu->v[1].f[0]);is_float=1;break;
        case 7: result_f=shyt_math_atanf(cpu->v[0].f[0]);is_float=1;break;
        case 8: result_d=shyt_math_exp(cpu->v[0].fd[0]);is_double=1;break;
        case 9: result_d=shyt_math_exp2(cpu->v[0].fd[0]);is_double=1;break;
        case 10:result_f=shyt_math_exp2f(cpu->v[0].f[0]);is_float=1;break;
        case 11:result_f=shyt_math_expf(cpu->v[0].f[0]);is_float=1;break;
        case 12:result_d=shyt_math_fmod(cpu->v[0].fd[0],cpu->v[1].fd[0]);is_double=1;break;
        case 13:result_f=shyt_math_fmodf(cpu->v[0].f[0],cpu->v[1].f[0]);is_float=1;break;
        case 14:result_d=shyt_math_frexp(cpu->v[0].fd[0],&exp);is_double=1;have_out=1;break;
        case 15:result_f=shyt_math_frexpf(cpu->v[0].f[0],&exp);is_float=1;have_out=1;break;
        case 16:result_d=shyt_math_ldexp(cpu->v[0].fd[0],(int)cpu->r[RDI]);is_double=1;break;
        case 17:result_f=shyt_math_ldexpf(cpu->v[0].f[0],(int)cpu->r[RDI]);is_float=1;break;
        case 18:result_d=shyt_math_pow(cpu->v[0].fd[0],cpu->v[1].fd[0]);is_double=1;break;
        case 19:result_f=shyt_math_powf(cpu->v[0].f[0],cpu->v[1].f[0]);is_float=1;break;
        case 20:result_d=shyt_math_tan(cpu->v[0].fd[0]);is_double=1;break;
        case 21:result_f=shyt_math_tanf(cpu->v[0].f[0]);is_float=1;break;
        case 22:result_f=shyt_math_tanhf(cpu->v[0].f[0]);is_float=1;break;
        default:goto bad;
        }
        if(have_out) {
            output_address=cpu->r[RDI];
            if(!shyt_guest_vm_probe_v385(&lease,output_address,4) ||
               (output_address < slot+8 &&
                slot < output_address+4))goto bad;
        }
    }
    /* All mutable memory locations were validated before any stores.
     * An active V383 lease prevents backing lifetime changes between
     * this preflight and the atomic commit. */
    if(have_out && !shyt_guest_vm_write_v385(
          &lease,output_address,4,(uint32_t)exp))goto bad;
    if(!shyt_guest_vm_write_v385(&lease,slot,8,next))goto bad;
    if(!shyt_guest_vm_unpin_v385(&lease))abort();
    if(is_double)cpu->v[0].fd[0]=result_d;
    if(is_float)cpu->v[0].f[0]=result_f;
    if(is_clock)cpu->r[RAX]=result_int;
    cpu->rip=next;
    return 1;
bad:
    if(!shyt_guest_vm_unpin_v385(&lease))abort();
    return 0;
}
static void import_call_v385(BbCpu *cpu,uint64_t target,uint64_t next) {
    ShytUnifiedImportV385 *r=atomic_load_explicit(
       &active_v385,memory_order_acquire);
    if(!r || !r->ready || !r->published)abort();
    int opcode=-1;
    if(target==r->clock_ticks)opcode=23;
    else if(target==r->clock_frequency)opcode=24;
    else for(size_t i=0;i<23;i++)
        if(target==r->math_targets[i]){opcode=(int)r->math_opcodes[i];break;}
    if(opcode<0) {
        r->native_fallback(cpu,target,next);
        return; /* missing AOT native target ABORTS inside V382 */
    }
    if(!handle_import(r,cpu,target,next,opcode))abort();
}
int shyt_unified_import_publish_v385(ShytUnifiedImportV385 *r) {
    ShytUnifiedImportV385 *expected=NULL;
    if(!r || r->ready!=1 || r->published ||
       !r->services || !r->vm || !r->native_fallback ||
       !r->services->native_only_finalized_v384 ||
       r->services->published_api!=&r->services->clock.api ||
       r->services->clock.api.call==import_call_v385 ||
       !shyt_native_stack_pin_v383(r->vm->stack))return 0;
    if(!shyt_native_stack_unpin_v383(r->vm->stack))abort();
    if(!atomic_compare_exchange_strong_explicit(
          &active_v385,&expected,r,memory_order_release,
          memory_order_acquire))return 0;
    /* Single-threaded boot ONLY: the generated module holds the same
     * pointer as V245's real final clock RcApi. */
    r->published=1;
    r->services->clock.api.call=import_call_v385;
    return 1;
}
