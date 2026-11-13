/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_string_v415.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V415_FAIL %d\n",__LINE__);abort();}}while(0)
static ShytNativeOsVmV388 vm;
static void body(BbCpu *cpu) {
    const ShytStrlenSiteV415 site={11,12,0x4000,0x4010,4};
    const ShytStrlenSiteV415 gap={11,12,0x4000,0x4018,4};
    CHECK(shyt_generated_try_store_v390(0x4000,8,0x4141));
    CHECK(shyt_generated_try_store_v390(0x4008,8,UINT64_C(0x6100626262626262)));
    cpu->r[7]=0x4000;
    CHECK(shyt_strlen_call_v415(&vm,&site,cpu,cpu,11,12) && cpu->r[0]==2 && cpu->rip==12);
    cpu->r[7]=0x4002;
    CHECK(shyt_strlen_call_v415(&vm,&site,cpu,cpu,11,12) && !cpu->r[0]);
    cpu->r[7]=0x400e;
    CHECK(shyt_strlen_call_v415(&vm,&site,cpu,cpu,11,12) && !cpu->r[0]);
    cpu->r[0]=99; cpu->rip=98; cpu->r[7]=0x4008;
    CHECK(!shyt_strlen_call_v415(&vm,&site,cpu,cpu,11,12));
    cpu->r[7]=0x400f;
    CHECK(!shyt_strlen_call_v415(&vm,&site,cpu,cpu,11,12));
    CHECK(!shyt_strlen_call_v415(&vm,&gap,cpu,cpu,11,12));
    cpu->r[7]=0x4000;
    CHECK(!shyt_strlen_call_v415(&vm,&site,cpu,cpu,11,13));
    CHECK(cpu->r[0]==99 && cpu->rip==98);
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
    puts("NATIVE_V415_STARTUP_STRING_PASS");
    return 0;
}
