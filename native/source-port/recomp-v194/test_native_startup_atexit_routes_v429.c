/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_atexit_routes_v429.h"
#include <stdio.h>
#include <stdlib.h>
#define C(x) do { if(!(x)){fprintf(stderr,"V429_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytAtexitV423 list;
static void fn(BbCpu *cpu){(void)cpu;}
static void body(BbCpu *cpu) {
    const RcFunction t[]={{.offset=0x30,.fn=fn}};
    const ShytAtexitTailSiteV425 rows[]={
        {7,{{0x10,0x20},{0x30,0x4000,0x4008}}},
        {9,{{0x10,0x20},{0x30,0x4008,0x4000}}}
    };
    ShytAtexitTailSiteV425 bad[]={rows[0],rows[0]};
    ShytAtexitRoutesV429 plan={0};
    C(!shyt_atexit_routes_init_v429(&plan,bad,2,t,1));
    bad[1]=rows[1];bad[1].registration.tuple.fn=0x31;
    C(!shyt_atexit_routes_init_v429(&plan,bad,2,t,1));
    C(!plan.rows && !plan.count);
    C(shyt_atexit_routes_init_v429(&plan,rows,2,t,1));
    cpu->rip=0x10; cpu->r[4]=0x4010; cpu->r[7]=0x30; cpu->r[6]=0x4000;
    cpu->r[2]=0x4008; cpu->r[0]=99;
    C(shyt_generated_try_store_v390(0x4010,8,0x21));
    C(!shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,7,0x4010,0x4018));
    C(shyt_generated_try_store_v390(0x4010,8,0x20));
    C(!shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,8,0x4010,0x4018));
    C(!shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,7,0x4011,0x4019));
    cpu->r[6]=0x4008;
    C(!shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,7,0x4010,0x4018));
    C(!list.count && cpu->rip==0x10 && cpu->r[4]==0x4010 && cpu->r[0]==99);
    cpu->r[6]=0x4000;
    C(shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,7,0x4010,0x4018));
    C(list.count==1 && cpu->rip==0x20 && cpu->r[4]==0x4018 && !cpu->r[0]);
    uint64_t word=0;
    C(shyt_generated_try_load_v390(0x4010,8,&word) && word==0x20);
    cpu->rip=0x10; cpu->r[4]=0x4010;
    C(!shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,9,0x4010,0x4018));
    cpu->r[6]=0x4008;cpu->r[2]=0x4000;
    C(shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,9,0x4010,0x4018));
    C(list.count==2 && list.entries[1].object==0x4008 && list.entries[1].dso==0x4000);
    cpu->rip=0x10; cpu->r[4]=0x4010; list.count=SHYT_ATEXIT_MAX_V423;
    C(shyt_atexit_route_tail_v429(&plan,&list,&vm,cpu,cpu,t,1,9,0x4010,0x4018));
    C(list.count==SHYT_ATEXIT_MAX_V423 && cpu->r[0]==UINT32_MAX &&
      cpu->rip==0x20 && cpu->r[4]==0x4018);
}
int main(void) {
    BbCpu cpu={0}; int code=-1;
    C(shyt_native_os_vm_init_v388(&vm));
    C(shyt_native_os_vm_add_v388(&vm,0x4000,8,SHYT_V386_READ|SHYT_V386_WRITE));
    C(shyt_native_os_vm_seal_v388(&vm));
    C(shyt_generated_call_recoverable_v393(&vm,body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    C(!code && shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V429_ATEXIT_ROUTES_PASS");
}
