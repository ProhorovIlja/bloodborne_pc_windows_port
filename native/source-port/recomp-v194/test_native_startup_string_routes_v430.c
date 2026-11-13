/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_string_routes_v430.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V430_FAIL %d\n",__LINE__);abort();}}while(0)
static ShytNativeOsVmV388 vm;
static void body(BbCpu *cpu) {
    const ShytStrlenSiteV415 rows[]={
        {11,12,0x4000,0x4004,8}, {11,12,0x4004,0x4008,8}, {11,12,0x400a,0x4010,4},
        {21,22,0x4000,0x4010,8}
    };
    ShytStringRoutesV430 plan={0};
    ShytStrlenSiteV415 bad[]={rows[0],rows[1]};
    bad[1].start=0x4003;
    CHECK(!shyt_string_routes_init_v430(&plan,bad,2));
    bad[1]=rows[1];bad[1].target=21;
    CHECK(!shyt_string_routes_init_v430(&plan,bad,2));
    CHECK(!plan.rows && !plan.count);
    CHECK(shyt_string_routes_init_v430(&plan,rows,4));
    CHECK(shyt_generated_try_store_v390(0x4000,8,UINT64_C(0x0000424241004141)));
    CHECK(shyt_generated_try_store_v390(0x4008,8,UINT64_C(0x0000000061000000)));
    cpu->r[7]=0x4000;
    CHECK(shyt_string_route_v430(&plan,&vm,cpu,cpu,11,12) && cpu->r[0]==2 && cpu->rip==12);
    cpu->r[7]=0x4004;
    CHECK(shyt_string_route_v430(&plan,&vm,cpu,cpu,11,12) && cpu->r[0]==2);
    cpu->r[0]=99;cpu->rip=98;cpu->r[7]=0x4003;
    CHECK(!shyt_string_route_v430(&plan,&vm,cpu,cpu,11,12));
    cpu->r[7]=0x4009;
    CHECK(!shyt_string_route_v430(&plan,&vm,cpu,cpu,11,12));
    cpu->r[7]=0x4000;
    CHECK(!shyt_string_route_v430(&plan,&vm,cpu,cpu,21,12));
    CHECK(!shyt_string_route_v430(&plan,&vm,cpu,cpu,11,13));
    CHECK(cpu->r[0]==99 && cpu->rip==98);
    CHECK(shyt_string_route_v430(&plan,&vm,cpu,cpu,21,22) && cpu->r[0]==2 && cpu->rip==22);
}
int main(void) {
    BbCpu cpu={0};
    int code=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,2,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && !shyt_generated_active_v390());
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V430_STRING_ROUTES_PASS");
    return 0;
}
