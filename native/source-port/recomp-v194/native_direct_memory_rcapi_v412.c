/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_direct_memory_import_v412.h"
#include <stdlib.h>
static _Thread_local ShytDmImport *active_dm;

/* rc->call is issued by the pinned emitter without a guest return push
 * for omitted import thunks. The audited target is the thunk address,
 * not the host implementation pointer or its loader-populated slot. */
void shyt_dm_rcapi_call_v412(BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!active_dm || shyt_generated_recovery_depth_v393()!=1u)abort();
    if(!shyt_dm_call_v412(active_dm,cpu,target,next))
        shyt_generated_raise_v393(SHYT_DM_CALL_DENIED_V412);
}
int shyt_dm_run_rcapi_v412(ShytDmImport *s,ShytGeneratedFnV392 fn,
    BbCpu *cpu,const ShytDmSite *sites,size_t count,int *code) {
    if(!s || active_dm)return SHYT_V393_DENIED;
    active_dm=s;
    const int result=shyt_dm_run_v412(s,fn,cpu,sites,count,code);
    active_dm=NULL;
    return result;
}
