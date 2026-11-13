/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_rcapi_v436.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V436_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytStartupDispatchV435 state;
static unsigned visits, after, mode;
static const RcApi api={.call=shyt_startup_rcapi_call_v436};

static void ret(BbCpu *cpu) {
    uint64_t next=0;
    CHECK(shyt_generated_try_load_v390(cpu->r[4],8,&next));
    cpu->rip=next;
    cpu->r[4]+=8;
}
static void leaf(BbCpu *cpu) {
    CHECK(cpu->rip==21 && cpu->r[4]==0x4010);
    ++visits;
    ret(cpu);
}
static void broken(BbCpu *cpu) {
    CHECK(cpu->rip==31);
    ++visits;
}
static void outer(BbCpu *cpu) {
    CHECK(cpu->rip==11 && cpu->r[4]==0x4018);
    int reason=-1;
    CHECK(shyt_startup_rcapi_run_v436(&state,2,leaf,&reason)==SHYT_V393_DENIED && !reason);
    api.call(cpu,mode==1 ? 31 : 21,12);
    ++visits;
    ret(cpu);
}
static void driver(BbCpu *cpu) {
    api.call(cpu,11,44);
    ++after;
}
static const RcFunction registry[]={
    {.offset=11,.fn=outer},{.offset=21,.fn=leaf},{.offset=31,.fn=broken}
};
static const ShytScopedCallV435 routes[]={
    {2,{21,12}}, {2,{11,44}}, {3,{31,12}}, {3,{11,44}}
};
static ShytBoundCallV435 bound[4];
static void setup(BbCpu *cpu) {
    state=(ShytStartupDispatchV435){0};
    *cpu=(BbCpu){0};
    cpu->r[4]=0x4020;
    CHECK(shyt_startup_dispatch_init_v435(&state,&vm,cpu,0x4000,0x4020,
        routes,4,registry,3,bound,4));
}
static void clean_scope(void) {
    CHECK(shyt_generated_recovery_depth_v393()==0u && !shyt_generated_owner_v392());
}
int main(void) {
    BbCpu cpu;
    int reason=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    setup(&cpu);
    CHECK(shyt_startup_rcapi_run_v436(&state,2,driver,&reason)==SHYT_V393_COMPLETED);
    CHECK(!reason && visits==2 && after==1 && cpu.rip==44 && cpu.r[4]==0x4020);
    clean_scope();
    CHECK(shyt_startup_rcapi_run_v436(&state,1,driver,&reason)==SHYT_V393_RECOVERED);
    CHECK(reason==SHYT_V436_CALL_DENIED && state.terminal && visits==2 && after==1);
    CHECK(cpu.rip==44 && cpu.r[4]==0x4020);
    clean_scope();
    CHECK(shyt_startup_rcapi_run_v436(&state,2,driver,&reason)==SHYT_V393_DENIED && !reason);
    setup(&cpu);
    mode=1;
    CHECK(shyt_startup_rcapi_run_v436(&state,2,driver,&reason)==SHYT_V393_RECOVERED);
    CHECK(reason==SHYT_V436_CALL_DENIED && visits==2 && after==1);
    CHECK(cpu.rip==11 && cpu.r[4]==0x4018);
    clean_scope();
    setup(&cpu);
    CHECK(shyt_startup_rcapi_run_v436(&state,3,driver,&reason)==SHYT_V393_RECOVERED);
    CHECK(reason==SHYT_V436_CALL_BAD_RETURN && state.terminal && visits==3 && after==1);
    CHECK(cpu.rip==31 && cpu.r[4]==0x4010);
    clean_scope();
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V436_STRICT_RCAPI_REPLAY_PASS");
    return 0;
}
