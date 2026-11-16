/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_crt_checked_boot_v448.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V438_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytStartupDispatchV435 state;
static ShytBoundCallV435 bound[4];
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
static const ShytScopedCallV435 routes[]={{1,{21,12}},{2,{21,12}},{7,{21,12}},{9,{21,12}}};
static void reset(BbCpu *cpu) {
    *cpu=(BbCpu){0}; cpu->r[4]=0x4020;
    state=(ShytStartupDispatchV435){0};
    CHECK(shyt_startup_dispatch_init_v435(&state,&vm,cpu,0x4000,0x4020,
        routes,4,registry,2,bound,4));
}
static int run(unsigned ordinal,uint64_t sentinel,int *why) {
    return shyt_startup_entry_v438(&state,ordinal,registry,2,11,sentinel,why);
}
static int post(BbCpu *cpu,uint32_t ordinal,uint64_t id,void *context) {
    unsigned *seen=context;
    uint64_t word=0;
    CHECK(shyt_generated_owner_v392()==&vm && cpu->rip==44 && id==11);
    CHECK(shyt_generated_try_load_v390(0x4018,8,&word) && word==44);
    ++*seen;
    return ordinal==7;
}
typedef struct { unsigned events, stop; } BootFixture;
static int boot_env(void *opaque,int argc,char *const *argv,char *const *envp) {
    BootFixture *f=opaque;
    CHECK(argc==1 && argv[0] && !envp);
    f->events=1;
    return 1;
}
static int boot_post(BbCpu *cpu,uint32_t ordinal,uint64_t id,void *opaque) {
    BootFixture *f=opaque;
    CHECK(cpu->rip==44 && id==11 && shyt_generated_owner_v392()==&vm);
    CHECK(f->events==ordinal);
    ++f->events;
    return ordinal!=f->stop;
}
static int boot_main(void *opaque,ShytCrtV409 *crt,int argc,char *const *argv,void *third) {
    BootFixture *f=opaque;
    CHECK(f->events==3 && crt->phase==SHYT_CRT_MAIN_V409 && argc==1 && argv[0] && !third);
    CHECK(!shyt_generated_owner_v392() && !shyt_generated_recovery_depth_v393());
    f->events=4;
    return 17;
}
static void boot_notify(void *opaque,int status) {
    BootFixture *f=opaque;
    CHECK(f->events==4 && status==17);
    f->events=5;
}
static void boot_image(void *opaque) {
    BootFixture *f=opaque;
    CHECK(f->events==(f->stop ? 3u : 5u));
    f->events=6;
}
static void boot_loader(void *opaque) {
    BootFixture *f=opaque;
    CHECK(f->events==6);
    f->events=7;
}
static void test_boot(BbCpu *cpu) {
    ShytCtorRowV427 rows[]={{1,11},{2,11}};
    char arg[]="native-test";
    char *argv[]={arg,NULL};
    for(unsigned stop=0;stop<=2;stop+=2) {
        BootFixture f={0,stop};
        ShytCrtV409 crt={0};
        const ShytCrtHooksV409 host={boot_env,{boot_loader,&f},{boot_image,&f},
            NULL,boot_main,boot_notify};
        ShytCheckedBootV448 p={.state=&state,.rows=rows,.count=1,.expected_count=2,
            .sentinel=44,.post=boot_post,.post_context=&f};
        int status=-99;
        reset(cpu);
        CHECK(!shyt_checked_boot_v448(&crt,&p,&host,&f,1,argv,NULL,&status));
        CHECK(crt.phase==SHYT_CRT_NEW_V409 && !f.events && status==-99);
        p.count=2;
        CHECK(shyt_checked_boot_v448(&crt,&p,&host,&f,1,argv,NULL,&status)==!stop);
        CHECK(f.events==7 && !crt.count);
        if(stop) {
            CHECK(p.result==SHYT_REPLAY_STOPPED && p.report.returned==1);
            CHECK(p.report.stopped_at==2 && p.report.reason==SHYT_V439_POSTCONDITION);
            CHECK(crt.phase==SHYT_CRT_FAILED_V409 && status==-99 && state.terminal);
        } else {
            CHECK(p.result==SHYT_REPLAY_COMPLETE && p.report.returned==2);
            CHECK(crt.phase==SHYT_CRT_DONE_V409 && status==17);
        }
    }
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
    reset(&cpu);
    unsigned seen=0;
    ShytReplayReportV437 report;
    ShytCtorRowV427 rows[]={{7,11},{8,99},{9,11}};
    RcFunction clone[]={{.offset=11,.fn=ctor},{.offset=21,.fn=leaf}};
    CHECK(shyt_startup_entry_v438(&state,7,clone,2,11,44,&why)==SHYT_V393_DENIED);
    CHECK(shyt_startup_retail_plan_v439(&state,rows,7,3,44,post,&seen,&report)==SHYT_REPLAY_REFUSED);
    CHECK(calls==4 && !seen && !state.terminal && !report.returned);
    rows[1].id=11;
    CHECK(shyt_startup_retail_plan_v439(&state,rows,7,3,44,post,&seen,&report)==SHYT_REPLAY_STOPPED);
    CHECK(report.returned==1 && report.stopped_at==8 && report.reason==SHYT_V436_CALL_DENIED);
    CHECK(calls==6 && seen==1 && state.terminal);
    reset(&cpu);
    rows[0].ordinal=9;
    CHECK(shyt_startup_retail_plan_v439(&state,rows,9,1,44,post,&seen,&report)==SHYT_REPLAY_STOPPED);
    CHECK(calls==7 && seen==2 && !report.returned && report.reason==SHYT_V439_POSTCONDITION);
    CHECK(state.terminal && !shyt_generated_owner_v392() && !shyt_generated_recovery_depth_v393());
    test_boot(&cpu);
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V439_INTEGRATED_CONSTRUCTOR_REPLAY_PASS");
    return 0;
}
