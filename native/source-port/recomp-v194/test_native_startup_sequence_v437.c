/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_sequence_v437.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V437_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytStartupDispatchV435 state;
static ShytBoundCallV435 bindings[2];
static unsigned entered;
static void leaf(BbCpu *cpu) {
    uint64_t word=0;
    CHECK(shyt_generated_try_load_v390(cpu->r[4],8,&word));
    cpu->rip=word; cpu->r[4]+=8; ++cpu->r[0];
}
static void first(BbCpu *cpu) {
    ++entered;
    shyt_startup_rcapi_call_v436(cpu,11,22);
    CHECK(shyt_generated_try_store_v390(0x4000,8,99));
}
static void second(BbCpu *cpu) {
    uint64_t word=0;
    ++entered;
    CHECK(shyt_generated_try_load_v390(0x4000,8,&word) && word==99);
    shyt_startup_rcapi_call_v436(cpu,11,33);
}
static const RcFunction table[]={{.offset=11,.fn=leaf}};
static const ShytScopedCallV435 routes[]={{7,{11,22}},{8,{11,33}}};
static void reset(BbCpu *cpu) {
    *cpu=(BbCpu){0}; cpu->r[4]=0x4020;
    entered=0;
    state=(ShytStartupDispatchV435){0};
    CHECK(shyt_startup_dispatch_init_v435(&state,&vm,cpu,0x4000,0x4020,routes,2,table,1,bindings,2));
}
int main(void) {
    BbCpu cpu;
    ShytReplayReportV437 report;
    ShytReplayStepV437 steps[]={{7,first,22},{8,second,33}};
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    reset(&cpu);
    steps[1].ordinal=9;
    CHECK(shyt_startup_sequence_v437(&state,steps,7,2,&report)==SHYT_REPLAY_REFUSED);
    CHECK(!entered && !report.returned && !state.terminal);
    steps[1].ordinal=8;
    CHECK(shyt_startup_sequence_v437(&state,steps,7,2,&report)==SHYT_REPLAY_COMPLETE);
    CHECK(entered==2 && cpu.r[0]==2 && report.returned==2 && !report.reason);
    reset(&cpu);
    steps[0].return_ip=23;
    CHECK(shyt_startup_sequence_v437(&state,steps,7,2,&report)==SHYT_REPLAY_STOPPED);
    CHECK(entered==1 && !report.returned && report.stopped_at==7 && state.terminal);
    CHECK(report.reason==SHYT_V437_OUTER_RETURN);
    CHECK(shyt_startup_sequence_v437(&state,steps,7,2,&report)==SHYT_REPLAY_REFUSED);
    reset(&cpu);
    steps[0].return_ip=22;
    steps[1].driver=first;
    CHECK(shyt_startup_sequence_v437(&state,steps,7,2,&report)==SHYT_REPLAY_STOPPED);
    CHECK(report.returned==1 && report.stopped_at==8 && report.reason==SHYT_V436_CALL_DENIED);
    CHECK(state.terminal && !shyt_generated_owner_v392() && !shyt_generated_recovery_depth_v393());
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V437_ORDERED_REPLAY_PASS");
    return 0;
}
