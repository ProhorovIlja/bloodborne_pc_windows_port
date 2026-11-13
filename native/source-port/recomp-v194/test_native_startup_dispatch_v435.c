/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_dispatch_v435.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V435_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm,other;
static ShytStartupDispatchV435 dispatch;
static int visits;
static void return_guest(BbCpu *cpu) {
    uint64_t ret=0;
    CHECK(shyt_generated_try_load_v390(cpu->r[4],8,&ret));
    cpu->rip=ret; cpu->r[4]+=8;
}
static void inner(BbCpu *cpu) {
    CHECK(cpu->rip==21 && cpu->r[4]==0x4010);
    ++visits; return_guest(cpu);
}
static void outer(BbCpu *cpu) {
    CHECK(cpu->rip==11 && cpu->r[4]==0x4018);
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1089,21,12)==SHYT_STARTUP_RETURNED);
    ++visits; return_guest(cpu);
}
static void broken(BbCpu *cpu) { (void)cpu; ++visits; }
static const RcFunction table[]={
    {.offset=11,.fn=outer},{.offset=21,.fn=inner},{.offset=31,.fn=broken}
};
static const ShytScopedCallV435 routes[]={
    {1088,{11,44}}, {1089,{21,12}}, {1089,{11,44}}, {1089,{31,44}}
};
static ShytBoundCallV435 bindings[4];
static void body(BbCpu *cpu) {
    BbCpu wrong={0};
    cpu->r[4]=0x4020;
    CHECK(shyt_startup_dispatch_v435(&dispatch,&wrong,1089,11,44)==SHYT_STARTUP_DENIED);
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1088,31,44)==SHYT_STARTUP_DENIED);
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1089,11,45)==SHYT_STARTUP_DENIED);
    CHECK(!visits && !cpu->rip && cpu->r[4]==0x4020);
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1089,11,44)==SHYT_STARTUP_RETURNED);
    CHECK(visits==2 && cpu->rip==44 && cpu->r[4]==0x4020);
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1089,31,44)==SHYT_STARTUP_BAD_RETURN);
    CHECK(visits==3 && dispatch.terminal && cpu->rip==31 && cpu->r[4]==0x4018);
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1089,11,44)==SHYT_STARTUP_BAD_RETURN);
    CHECK(visits==3 && cpu->rip==31 && cpu->r[4]==0x4018);
}
static void wrong_owner(BbCpu *cpu) {
    CHECK(shyt_startup_dispatch_v435(&dispatch,cpu,1089,11,44)==SHYT_STARTUP_DENIED);
    CHECK(!visits && !cpu->rip && cpu->r[4]==0x4020);
}
static void open_vm(ShytNativeOsVmV388 *m) {
    CHECK(shyt_native_os_vm_init_v388(m));
    CHECK(shyt_native_os_vm_add_v388(m,0x4000,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(m));
}
int main(void) {
    BbCpu cpu={0}; int code=-1;
    const ShytScopedCallV435 missing[]={{1089,{11,12}},{1089,{91,13}}};
    const ShytScopedCallV435 duplicate[]={{1089,{11,12}},{1089,{11,12}}};
    const RcFunction unsorted[]={{.offset=21,.fn=inner},{.offset=11,.fn=outer}};
    open_vm(&vm); open_vm(&other);
    bindings[0].row=table+2;
    CHECK(!shyt_startup_dispatch_init_v435(&dispatch,&vm,&cpu,0x4000,0x4020,missing,2,table,3,bindings,4));
    CHECK(!shyt_startup_dispatch_init_v435(&dispatch,&vm,&cpu,0x4000,0x4020,duplicate,2,table,3,bindings,4));
    CHECK(!shyt_startup_dispatch_init_v435(&dispatch,&vm,&cpu,0x4000,0x4020,routes,4,unsorted,2,bindings,4));
    CHECK(!shyt_startup_dispatch_init_v435(&dispatch,&vm,&cpu,0x4000,0x4020,routes,4,table,3,bindings,3));
    CHECK(!dispatch.count && bindings[0].row==table+2 && !bindings[1].row);
    CHECK(shyt_startup_dispatch_init_v435(&dispatch,&vm,&cpu,0x4000,0x4020,routes,4,table,3,bindings,4));
    CHECK(bindings[0].row==table && bindings[1].row==table+1 && bindings[3].row==table+2);
    cpu.r[4]=0x4020;
    CHECK(shyt_startup_dispatch_v435(&dispatch,&cpu,1089,11,44)==SHYT_STARTUP_DENIED);
    CHECK(shyt_generated_call_recoverable_v393(&other,wrong_owner,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    CHECK(shyt_native_os_vm_close_v388(&other) && shyt_native_os_vm_release_v388(&other,1));
    puts("NATIVE_V435_SCOPED_CALL_DISPATCH_PASS");
    return 0;
}
