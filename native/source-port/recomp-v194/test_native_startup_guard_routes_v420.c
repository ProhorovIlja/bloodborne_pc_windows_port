/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_guard_routes_v420.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"guard route failure %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static void body(BbCpu *c) {
    const ShytGuardSiteV413 rows[]={
        {0x10,0x20,0x4000,SHYT_GUARD_ACQUIRE},
        {0x10,0x20,0x4008,SHYT_GUARD_ACQUIRE},
        {0x30,0x40,0x4000,SHYT_GUARD_RELEASE},
        {0x50,0x60,0x4008,SHYT_GUARD_ABORT},
    };
    ShytGuardSiteV413 bad[]={rows[0],rows[1]};
    ShytGuardRoutesV420 r={0}; uint64_t word=99;
    bad[1].guard=bad[0].guard;
    CHECK(!shyt_guard_routes_init_v420(&r,bad,2));
    bad[1]=rows[1]; bad[1].action=SHYT_GUARD_ABORT;
    CHECK(!shyt_guard_routes_init_v420(&r,bad,2));
    bad[1]=rows[1]; bad[1].target=0x50;
    CHECK(!shyt_guard_routes_init_v420(&r,bad,2));
    bad[1]=rows[1]; bad[1].next=0x1f;
    CHECK(!shyt_guard_routes_init_v420(&r,bad,2));
    CHECK(!r.rows && !r.count && shyt_guard_routes_init_v420(&r,rows,4));
    CHECK(!shyt_guard_routes_init_v420(&r,rows,4));
    c->r[4]=0x4020;
    c->r[0]=99; c->rip=98; c->r[7]=0x4010;
    CHECK(!shyt_guard_dispatch_v420(&r,&vm,c,c,0x10,0x20));
    c->r[7]=0x4008;
    CHECK(!shyt_guard_dispatch_v420(&r,&vm,c,c,0x30,0x20));
    CHECK(!shyt_guard_dispatch_v420(&r,&vm,c,c,0x30,0x40));
    CHECK(c->r[0]==99 && c->rip==98);
    CHECK(shyt_guard_dispatch_v420(&r,&vm,c,c,0x10,0x20) && c->r[0]==1 && c->rip==0x20);
    CHECK(!shyt_guard_dispatch_v420(&r,&vm,c,c,0x10,0x20));
    CHECK(shyt_generated_try_load_v390(0x4000,8,&word) && !word);
    CHECK(shyt_guard_dispatch_v420(&r,&vm,c,c,0x50,0x60));
    CHECK(shyt_generated_try_load_v390(0x4008,8,&word) && !word);
    c->r[7]=0x4000;
    CHECK(shyt_guard_dispatch_v420(&r,&vm,c,c,0x10,0x20) && c->r[0]==1);
    CHECK(shyt_guard_dispatch_v420(&r,&vm,c,c,0x30,0x40));
    CHECK(shyt_guard_dispatch_v420(&r,&vm,c,c,0x10,0x20) && c->r[0]==0);
    CHECK(shyt_generated_try_load_v390(0x4000,8,&word) && word==1);
}
int main(void) {
    BbCpu c={0}; int code=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,8,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&c,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V420_GUARD_ROUTES_PASS");
    return 0;
}
