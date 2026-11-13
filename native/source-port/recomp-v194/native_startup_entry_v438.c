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
} EntryV438;
static _Thread_local const EntryV438 *active_entry;

static void enter(BbCpu *cpu) {
    const EntryV438 *e=active_entry;
    if(!e || cpu!=e->state->cpu)abort();
    const uint64_t sp=cpu->r[4];
    const uint64_t lo=e->state->stack_lo,hi=e->state->stack_hi;
    if(hi<=lo || hi-lo<8u || (sp&7u) || sp<lo+8u || sp>hi ||
       !shyt_generated_try_probe_v390(sp-8u,8,SHYT_V386_READ|SHYT_V386_WRITE) ||
       !shyt_generated_try_store_v390(sp-8u,8,e->sentinel))
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

int shyt_startup_entry_checked_v439(ShytStartupDispatchV435 *state,uint32_t ordinal,
    uint64_t entry,uint64_t sentinel,ShytCtorPostV439 post,void *context,int *reason) {
    const RcFunction *registry=state ? state->registry : NULL;
    const size_t count=state ? state->registry_count : 0;
    if(reason)*reason=0;
    if(active_entry || !state || state->terminal || !registry || !count ||
       count>SHYT_CTOR_REG_LIMIT_V427 || !entry || !sentinel || entry==sentinel)
        return SHYT_V393_DENIED;
    const RcFn fn=shyt_startup_find_v418(registry,count,entry);
    if(!fn || shyt_startup_find_v418(registry,count,sentinel))return SHYT_V393_DENIED;
    const EntryV438 e={state,fn,entry,sentinel,ordinal,post,context};
    active_entry=&e;
    const int result=shyt_startup_rcapi_run_v436(state,ordinal,enter,reason);
    active_entry=NULL;
    return result;
}

int shyt_startup_entry_v438(ShytStartupDispatchV435 *state,uint32_t ordinal,
    const RcFunction *registry,size_t count,uint64_t entry,uint64_t sentinel,int *reason) {
    if(reason)*reason=0;
    if(!state || registry!=state->registry || count!=state->registry_count)
        return SHYT_V393_DENIED;
    return shyt_startup_entry_checked_v439(state,ordinal,entry,sentinel,NULL,NULL,reason);
}
