/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_static_guard_import_v413.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V413_FAIL_LINE %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static const uint64_t data=UINT64_C(0x600000000000);
static const uint64_t stack=UINT64_C(0x500000000000);
static void body(BbCpu *cpu) {
    ShytGuardSiteV413 site={11,12,data,SHYT_GUARD_ACQUIRE};
    uint64_t word=9;
    BbCpu other={0};
    cpu->r[7]=data; cpu->r[4]=stack; cpu->r[0]=99;
    CHECK(!shyt_guard_call_v413(&vm,&site,cpu,&other,11,12));
    CHECK(!shyt_guard_call_v413(&vm,&site,cpu,cpu,11,13));
    CHECK(shyt_generated_try_load_v390(data,8,&word)&&word==0 && cpu->r[0]==99);
    cpu->r[4]=data+1;
    CHECK(!shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12));
    cpu->r[4]=stack;
    CHECK(shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12) && cpu->r[0]==1 && cpu->rip==12);
    CHECK(shyt_generated_try_load_v390(data,8,&word)&&word==0x100);
    CHECK(!shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12));
    site.action=SHYT_GUARD_ABORT;
    CHECK(shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12));
    CHECK(shyt_generated_try_load_v390(data,8,&word)&&word==0);
    site.action=SHYT_GUARD_ACQUIRE;
    CHECK(shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12) && cpu->r[0]==1);
    site.action=SHYT_GUARD_RELEASE;
    CHECK(shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12));
    CHECK(shyt_generated_try_load_v390(data,8,&word)&&word==1);
    CHECK(!shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12));
    site.action=SHYT_GUARD_ACQUIRE;
    CHECK(shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12) && cpu->r[0]==0);
    CHECK(shyt_generated_try_store_v390(data,8,0x101));
    CHECK(!shyt_guard_call_v413(&vm,&site,cpu,cpu,11,12));
    CHECK(shyt_generated_try_load_v390(data,8,&word)&&word==0x101);
}
int main(void) {
    BbCpu cpu={0};int code=-1;
    const ShytGuardSiteV413 site={11,12,data,SHYT_GUARD_ACQUIRE};
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,data,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(!shyt_guard_call_v413(&vm,&site,&cpu,&cpu,11,12));
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(code==0 && !shyt_generated_active_v390());
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V413_GUARD_IMPORT_PASS");
    return 0;
}
