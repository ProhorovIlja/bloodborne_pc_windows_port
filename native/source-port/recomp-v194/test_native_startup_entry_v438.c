/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_entry_v438.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V438_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytStartupDispatchV435 state;
static ShytBoundCallV435 bound[1];
static unsigned calls,mode;
static void leaf(BbCpu *cpu) {
    uint64_t ret=0;
    CHECK(shyt_generated_try_load_v390(cpu->r[4],8,&ret));
    cpu->rip=ret; cpu->r[4]+=8;
}
static void ctor(BbCpu *cpu) {
    CHECK(cpu->rip==11 && cpu->r[4]==0x4018);
    ++calls;
    shyt_startup_rcapi_call_v436(cpu,21,12);
    CHECK(cpu->rip==12 && cpu->r[4]==0x4018);
    leaf(cpu);
    if(mode==1)CHECK(shyt_generated_try_store_v390(0x4018,8,99));
    if(mode==2)cpu->r[4]-=8;
}
static const RcFunction registry[]={{.offset=11,.fn=ctor},{.offset=21,.fn=leaf}};
static const ShytScopedCallV435 routes[]={{7,{21,12}}};
static void reset(BbCpu *cpu) {
    *cpu=(BbCpu){0}; cpu->r[4]=0x4020;
    state=(ShytStartupDispatchV435){0};
    CHECK(shyt_startup_dispatch_init_v435(&state,&vm,cpu,0x4000,0x4020,
        routes,1,registry,2,bound,1));
}
static int run(unsigned ordinal,uint64_t sentinel,int *why) {
    return shyt_startup_entry_v438(&state,ordinal,registry,2,11,sentinel,why);
}
int main(void) {
    BbCpu cpu;
    int why=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    reset(&cpu);
    CHECK(run(7,21,&why)==SHYT_V393_DENIED && !why && !calls && !cpu.rip);
    CHECK(run(7,44,&why)==SHYT_V393_COMPLETED && !why && calls==1);
    CHECK(cpu.rip==44 && cpu.r[4]==0x4020);
    for(mode=1;mode<=2;++mode) {
        reset(&cpu);
        CHECK(run(7,44,&why)==SHYT_V393_RECOVERED && why==SHYT_V438_BAD_OUTER_RETURN);
        CHECK(state.terminal && run(7,44,&why)==SHYT_V393_DENIED);
    }
    reset(&cpu);
    cpu.r[4]=0x4000;
    CHECK(run(7,44,&why)==SHYT_V393_RECOVERED && why==SHYT_V438_BAD_ENTRY_STACK);
    CHECK(calls==3 && !cpu.rip && cpu.r[4]==0x4000 && state.terminal);
    reset(&cpu);
    mode=0;
    CHECK(run(8,44,&why)==SHYT_V393_RECOVERED && why==SHYT_V436_CALL_DENIED);
    CHECK(calls==4 && state.terminal && !shyt_generated_owner_v392());
    CHECK(!shyt_generated_recovery_depth_v393());
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V438_CHECKED_CONSTRUCTOR_ENTRY_PASS");
    return 0;
}
