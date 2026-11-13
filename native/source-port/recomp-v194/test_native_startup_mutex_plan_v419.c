/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "native_startup_mutex_plan_v419.h"
#include <stdlib.h>
#include <stdio.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V419_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytStartupMutexStateV413 objects[2];
#define SITES {{11,21,SHYT_MUTEX_ATTR_INIT},{12,22,SHYT_MUTEX_ATTR_TYPE}, \
               {13,23,SHYT_MUTEX_INIT},{14,24,SHYT_MUTEX_ATTR_DESTROY}}
static const ShytMutexStepV419 plan[]={{0,SITES},{1,SITES}};
static void body(BbCpu *cpu) {
    ShytMutexCursorV419 c={0};
    uint64_t word;
    ShytMutexStepV419 bad[]={plan[0],plan[0]};
    CHECK(!shyt_mutex_plan_valid_v419(bad,2,2));
    CHECK(shyt_mutex_plan_valid_v419(plan,2,2));
    cpu->r[4]=0x4020;
    cpu->r[7]=0x4000;
    CHECK(!shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,12,22));
    CHECK(!shyt_mutex_plan_complete_v419(&c,2));
    for(size_t i=0;i<2;++i) {
        cpu->r[7]=0x4000;
        CHECK(shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,11,21) && !cpu->r[0]);
        CHECK(objects[i].live_attr);
        cpu->r[6]=3;
        CHECK(shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,12,22) &&
              cpu->r[0]==SHYT_MUTEX_EINVAL_V413 && c.op==1 && c.step==i);
        cpu->r[6]=2;
        CHECK(shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,12,22) && !cpu->r[0]);
        cpu->r[6]=0x4000;cpu->r[7]=objects[1-i].mutex_slot;
        CHECK(shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,13,23) &&
              cpu->r[0]==SHYT_MUTEX_EINVAL_V413 && c.op==2 && c.step==i);
        cpu->r[7]=objects[i].mutex_slot;
        CHECK(shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,13,23) && !cpu->r[0]);
        cpu->r[7]=0x4000;
        CHECK(shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,14,24) && !cpu->r[0]);
        CHECK(shyt_generated_try_load_v390(0x4000,8,&word) && !word);
        CHECK(objects[i].host.live && !objects[i].live_attr);
    }
    CHECK(shyt_mutex_plan_complete_v419(&c,2));
    CHECK(!shyt_mutex_plan_call_v419(plan,2,&c,objects,2,cpu,cpu,11,21));
    for(size_t i=0;i<2;++i)
        CHECK(shyt_generated_try_load_v390(objects[i].mutex_slot,8,&word) &&
              word==SHYT_MUTEX_OBJECT_TOKEN_V413);
}
int main(void) {
    BbCpu cpu={0};int code=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,8,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    for(size_t i=0;i<2;++i) {
        objects[i].owner=&vm;objects[i].attr_slot=0x4000;objects[i].mutex_slot=0x4008+8*i;
    }
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code);
    for(size_t i=0;i<2;++i)CHECK(shyt_startup_mutex_destroy_v413(&objects[i].host));
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V419_ORDERED_MUTEX_PLAN_PASS");
    return 0;
}
