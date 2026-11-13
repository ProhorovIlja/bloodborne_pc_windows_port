/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_direct_memory_import_v412.h"
#include "native_os_vm_reconfigure_v389.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V412_FAIL_LINE %d\n",__LINE__);abort();} }while(0)
enum { A=0,C=1,D=2,SP=4,SI=6,DI=7,U=8,V=9 };
static const uint64_t mem=UINT64_C(0x600000000000), out=UINT64_C(0x500000000000);
static const uint64_t len=UINT64_C(121634816), align=UINT64_C(2097152);
static const ShytDmSite sites[]={{0x11,0x101,SHYT_DM_SIZE},
    {0x12,0x102,SHYT_DM_ALLOC},{0x13,0x103,SHYT_DM_MAP},{0x14,0x104,SHYT_DM_FREE}};
static ShytDmImport state;
static int mode;
static const RcApi api={.call=shyt_dm_rcapi_call_v412};
static void invoke(BbCpu *cpu,size_t i,uint64_t expected) {
    api.call(cpu,sites[i].target,sites[i].next);
    CHECK(cpu->r[A]==expected && cpu->rip==sites[i].next);
}
static void body(BbCpu *cpu) {
    uint64_t word=0;
    if(mode) {
        CHECK(!shyt_generated_try_probe_v390(mem,8,SHYT_V386_READ));
        api.call(cpu,sites[0].target,sites[1].next);
        abort();
    }
    BbCpu other={0};
    CHECK(!shyt_dm_call_v412(&state,&other,sites[0].target,sites[0].next));
    CHECK(!shyt_dm_call_v412(&state,cpu,sites[0].target,sites[1].next));
    CHECK(!shyt_generated_try_load_v390(mem,8,&word));
    CHECK(!shyt_native_os_vm_pause_v389(state.owner));
    invoke(cpu,0,len);
    cpu->r[SP]=out+32;
    cpu->r[DI]=0;cpu->r[SI]=len;cpu->r[D]=len;cpu->r[C]=align;cpu->r[U]=0;
    cpu->r[V]=out+32;
    invoke(cpu,1,SHYT_DM_EFAULT);
    CHECK(!state.pool.count);
    cpu->r[V]=out;
    invoke(cpu,1,0);
    CHECK(shyt_generated_try_load_v390(out,8,&word) && word==0);
    cpu->r[DI]=out+8;cpu->r[SI]=len;cpu->r[D]=3;cpu->r[C]=1;cpu->r[U]=word;cpu->r[V]=align;
    invoke(cpu,2,SHYT_DM_ENOTSUP);
    CHECK(!state.length && state.pool.count==1);
    cpu->r[C]=0;
    CHECK(shyt_generated_try_store_v390(out+8,8,5));
    invoke(cpu,2,SHYT_DM_ENOTSUP);
    CHECK(shyt_generated_try_load_v390(out+8,8,&word) && word==5);
    CHECK(shyt_generated_try_store_v390(out+8,8,0));
    invoke(cpu,2,0);
    CHECK(shyt_generated_try_load_v390(out+8,8,&word) && word==mem);
    CHECK(!shyt_generated_try_probe_v390(mem+len-4,8,SHYT_V386_WRITE));
    CHECK(shyt_generated_try_load_v390(mem+len-8,8,&word) && !word);
    CHECK(shyt_generated_try_store_v390(mem+len-8,8,0xf00));
    CHECK(shyt_generated_try_store_v390(mem,8,0x1234));
    CHECK(!shyt_generated_try_probe_v390(mem,8,SHYT_V386_EXECUTE));
    cpu->r[DI]=0;cpu->r[SI]=len-SHYT_DM_PAGE;
    invoke(cpu,3,SHYT_DM_ENOTSUP);
    CHECK(shyt_generated_try_load_v390(mem,8,&word) && word==0x1234);
    cpu->r[SI]=len;
    invoke(cpu,3,0);
    CHECK(!state.length && !state.pool.count);
    CHECK(!shyt_generated_try_load_v390(mem,8,&word));
    CHECK(!shyt_generated_try_store_v390(mem+len-8,8,1));
    cpu->r[D]=len;cpu->r[C]=align;cpu->r[U]=0;cpu->r[V]=out;
    invoke(cpu,1,0);
    cpu->r[DI]=out+8;cpu->r[D]=3;cpu->r[C]=0;cpu->r[V]=align;
    CHECK(shyt_generated_try_store_v390(out+8,8,0));
    invoke(cpu,2,0);
    CHECK(shyt_generated_try_load_v390(mem,8,&word) && !word);
    CHECK(shyt_generated_try_load_v390(mem+len-8,8,&word) && !word);
    cpu->r[DI]=0;cpu->r[SI]=len;
    invoke(cpu,3,0);
}
int main(void) {
    ShytNativeOsVmV388 vm={0}; BbCpu cpu={0}; int code=-1;
    state.owner=&vm;state.base=mem;
    CHECK(shyt_dm_init(&state.pool,len));
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,out,16,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&vm,mem,(size_t)(len/8),SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(!shyt_dm_call_v412(&state,&cpu,sites[0].target,sites[0].next));
    CHECK(shyt_dm_run_rcapi_v412(&state,body,&cpu,sites,4,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && !shyt_generated_active_v390() && !state.cpu && !state.sites);
    CHECK(shyt_generated_enter_v390(&vm));
    CHECK(shyt_dm_run_rcapi_v412(&state,body,&cpu,sites,4,&code)==SHYT_V393_DENIED);
    CHECK(shyt_generated_active_v390() && shyt_generated_leave_v390());
    mode=1;
    CHECK(shyt_dm_run_rcapi_v412(&state,body,&cpu,sites,4,&code)==SHYT_V393_RECOVERED);
    CHECK(!state.cpu && !state.sites);
    CHECK(code==SHYT_DM_CALL_DENIED_V412 && !shyt_generated_active_v390() && !shyt_generated_recovery_depth_v393());
    mode=0;
    CHECK(shyt_dm_run_rcapi_v412(&state,body,&cpu,sites,4,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && !state.cpu);
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V412_DIRECT_MEMORY_IMPORT_SEQUENCE_PASS");
    return 0;
}
