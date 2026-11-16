/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_entry_v438.h"
#include <stdlib.h>

typedef struct {
    ShytStartupDispatchV435 *state;
    RcFn body;
    uint64_t entry,sentinel;
    uint32_t ordinal;
    ShytCtorPostV439 post;
    void *context;
    char *const *argv;
    uint64_t guest_argv;
    size_t capacity;
    int argc;
} EntryV438;
static _Thread_local const EntryV438 *active_entry;

/* Build a bounded, terminated x86-64 argv array in VM memory. Do all
 * shape/permission checks before publishing arguments or mutating CPU. */
static void main_args(BbCpu *cpu,const EntryV438 *e) {
    const uint64_t base=e->guest_argv;
    size_t used=8u*((size_t)e->argc+1u);
    size_t lengths[64];
    if(!base || (base&7u) || e->capacity>65536u || used>e->capacity ||
       base>UINT64_MAX-e->capacity ||
       (base<e->state->stack_hi && base+e->capacity>e->state->stack_lo))
        shyt_generated_raise_v393(SHYT_V449_BAD_MAIN_ARGS);
    for(int i=0;i<e->argc;++i) {
        size_t n=0;
        while(n<e->capacity-used && e->argv[i][n])++n;
        if(n==e->capacity-used)shyt_generated_raise_v393(SHYT_V449_BAD_MAIN_ARGS);
        lengths[i]=n+1;
        used+=n+1;
    }
    if(!shyt_generated_try_probe_v390(base,used,SHYT_V386_READ|SHYT_V386_WRITE))
        shyt_generated_raise_v393(SHYT_V449_BAD_MAIN_ARGS);
    uint64_t cursor=base+8u*((size_t)e->argc+1u);
    for(int i=0;i<e->argc;++i) {
        if(!shyt_generated_try_store_v390(base+8u*(size_t)i,8,cursor))
            shyt_generated_raise_v393(SHYT_V449_BAD_MAIN_ARGS);
        for(size_t j=0;j<lengths[i];++j)
            if(!shyt_generated_try_store_v390(cursor++,1,(unsigned char)e->argv[i][j]))
                shyt_generated_raise_v393(SHYT_V449_BAD_MAIN_ARGS);
    }
    if(!shyt_generated_try_store_v390(base+8u*(size_t)e->argc,8,0))
        shyt_generated_raise_v393(SHYT_V449_BAD_MAIN_ARGS);
    /* Guest SysV: RDI, RSI, RDX. The retail wrapper supplies a null third arg. */
    cpu->r[7]=(uint64_t)e->argc;
    cpu->r[6]=base;
    cpu->r[2]=0;
}

static void enter(BbCpu *cpu) {
    const EntryV438 *e=active_entry;
    if(!e || cpu!=e->state->cpu)abort();
    const uint64_t sp=cpu->r[4];
    const uint64_t lo=e->state->stack_lo,hi=e->state->stack_hi;
    if(hi<=lo || hi-lo<8u || (sp&7u) || sp<lo+8u || sp>hi ||
       !shyt_generated_try_probe_v390(sp-8u,8,SHYT_V386_READ|SHYT_V386_WRITE))
        shyt_generated_raise_v393(SHYT_V438_BAD_ENTRY_STACK);
    if(e->argv)main_args(cpu,e);
    if(!shyt_generated_try_store_v390(sp-8u,8,e->sentinel))
        shyt_generated_raise_v393(SHYT_V438_BAD_ENTRY_STACK);
    cpu->r[4]=sp-8u;
    cpu->rip=e->entry;
    e->body(cpu);
    uint64_t word=0;
    if(cpu->rip!=e->sentinel || cpu->r[4]!=sp ||
       !shyt_generated_try_load_v390(sp-8u,8,&word) || word!=e->sentinel)
        shyt_generated_raise_v393(SHYT_V438_BAD_OUTER_RETURN);
    if(e->post && !e->post(cpu,e->ordinal,e->entry,e->context))
        shyt_generated_raise_v393(SHYT_V439_POSTCONDITION);
}

static int run_entry(EntryV438 e,int *reason) {
    ShytStartupDispatchV435 *state=e.state;
    const uint64_t entry=e.entry,sentinel=e.sentinel;
    const RcFunction *registry=state ? state->registry : NULL;
    const size_t count=state ? state->registry_count : 0;
    if(reason)*reason=0;
    if(active_entry || !state || state->terminal || !registry || !count ||
       count>SHYT_CTOR_REG_LIMIT_V427 || !entry || !sentinel || entry==sentinel)
        return SHYT_V393_DENIED;
    const RcFn fn=shyt_startup_find_v418(registry,count,entry);
    if(!fn || shyt_startup_find_v418(registry,count,sentinel))return SHYT_V393_DENIED;
    e.body=fn;
    active_entry=&e;
    const int result=shyt_startup_rcapi_run_v436(state,e.ordinal,enter,reason);
    active_entry=NULL;
    return result;
}

int shyt_startup_entry_checked_v439(ShytStartupDispatchV435 *state,uint32_t ordinal,
    uint64_t entry,uint64_t sentinel,ShytCtorPostV439 post,void *context,int *reason) {
    if(ordinal>SHYT_CTOR_LIMIT_V427) {
        if(reason)*reason=0;
        return SHYT_V393_DENIED;
    }
    return run_entry((EntryV438){.state=state,.entry=entry,.sentinel=sentinel,
        .ordinal=ordinal,.post=post,.context=context},reason);
}

int shyt_startup_main_v449(ShytStartupDispatchV435 *state,
    uint64_t entry,uint64_t sentinel,int argc,char *const *argv,
    uint64_t guest_argv,size_t capacity,int32_t *status,int *reason) {
    if(reason)*reason=0;
    if(!status || argc<0 || argc>64 || !argv || argv[argc] ||
       (state && ((state->cpu && (state->cpu->r[4]&15u)) || guest_argv==0)))
        return SHYT_V393_DENIED;
    for(int i=0;i<argc;++i)if(!argv[i])return SHYT_V393_DENIED;
    const int result=run_entry((EntryV438){.state=state,.entry=entry,.sentinel=sentinel,
        .ordinal=SHYT_STARTUP_MAIN_SCOPE_V449,.argv=argv,.guest_argv=guest_argv,
        .capacity=capacity,.argc=argc},reason);
    if(result==SHYT_V393_COMPLETED) {
        const uint32_t eax=(uint32_t)state->cpu->r[0];
        *status=(int32_t)(eax<=INT32_MAX ? (int64_t)eax : (int64_t)eax-INT64_C(4294967296));
    }
    return result;
}

int shyt_startup_entry_v438(ShytStartupDispatchV435 *state,uint32_t ordinal,
    const RcFunction *registry,size_t count,uint64_t entry,uint64_t sentinel,int *reason) {
    if(reason)*reason=0;
    if(!state || registry!=state->registry || count!=state->registry_count)
        return SHYT_V393_DENIED;
    return shyt_startup_entry_checked_v439(state,ordinal,entry,sentinel,NULL,NULL,reason);
}
