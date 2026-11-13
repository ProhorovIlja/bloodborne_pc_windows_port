/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "native_startup_mutex_import_v413.h"
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
static ShytStartupMutexStateV413 mutex_state;
static void mutex_body(BbCpu *cpu) {
    ShytStartupMutexSiteV413 site={21,22,SHYT_MUTEX_ATTR_INIT};
    uint64_t w=0;
    cpu->r[4]=stack;
    cpu->r[7]=data+8u;
    CHECK(!shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,23));
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && !cpu->r[0]);
    CHECK(shyt_generated_try_load_v390(data+8u,8,&w) && w==SHYT_MUTEX_ATTR_TOKEN_V413);
    site.op=SHYT_MUTEX_ATTR_TYPE;
    cpu->r[6]=3;
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && cpu->r[0]==SHYT_MUTEX_EINVAL_V413);
    cpu->r[6]=2;
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && !cpu->r[0]);
    site.op=SHYT_MUTEX_INIT;
    cpu->r[7]=data+16u;
    cpu->r[6]=data+8u;
    cpu->r[2]=1;
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && cpu->r[0]==SHYT_MUTEX_EINVAL_V413);
    CHECK(!mutex_state.host.live && shyt_generated_try_load_v390(data+16u,8,&w) && !w);
    cpu->r[2]=0;
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && !cpu->r[0]);
    CHECK(mutex_state.host.live && shyt_generated_try_load_v390(data+16u,8,&w) && w==SHYT_MUTEX_OBJECT_TOKEN_V413);
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && cpu->r[0]==SHYT_MUTEX_EINVAL_V413);
    site.op=SHYT_MUTEX_ATTR_DESTROY;
    cpu->r[7]=data+8u;
    CHECK(shyt_mutex_call_v413(&mutex_state,&site,cpu,cpu,21,22) && !cpu->r[0]);
    CHECK(!mutex_state.live_attr && shyt_generated_try_load_v390(data+8u,8,&w) && !w);
    CHECK(shyt_startup_mutex_lock_v413(&mutex_state.host));
    CHECK(shyt_startup_mutex_try_v413(&mutex_state.host));
    CHECK(shyt_startup_mutex_unlock_v413(&mutex_state.host) && shyt_startup_mutex_unlock_v413(&mutex_state.host));
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
    mutex_state.owner=&vm;
    mutex_state.attr_slot=data+8u;
    mutex_state.mutex_slot=data+16u;
    CHECK(shyt_generated_call_recoverable_v393(&vm,mutex_body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && shyt_startup_mutex_destroy_v413(&mutex_state.host));
    puts("NATIVE_V413_MUTEX_IMPORT_PASS");
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V413_GUARD_IMPORT_PASS");
    return 0;
}
