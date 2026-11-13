/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_atexit_v423.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V423_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytAtexitV423 list;
static uint64_t order[4];
static size_t n;
static void placeholder(BbCpu *c){(void)c;}
static int invoke(void *p,ShytDtorV423 t) {
    CHECK(!shyt_atexit_finalize_v423(p,0,invoke,p));
    CHECK(n<4);order[n++]=t.object;return t.object!=0x4020;
}
static void body(BbCpu *c) {
    const RcFunction table[]={{.offset=10,.fn=placeholder}};
    ShytAtexitSiteV423 site={{30,40},{10,0x4000,0x4008}};
    c->r[7]=10;c->r[6]=0x4000;c->r[2]=0x4010;
    CHECK(!shyt_atexit_call_v423(&list,&vm,c,c,table,1,&site,30,40) && !list.count && !c->rip);
    c->r[2]=0x4008;
    CHECK(!shyt_atexit_call_v423(&list,&vm,c,c,table,1,&site,30,41));
    CHECK(!shyt_atexit_finalize_v423(&list,0,invoke,&list));
    for(unsigned i=0;i<3;i++) {
        site.tuple.object=0x4000+8*i;c->r[6]=site.tuple.object;
        site.tuple.dso=i==1?0x4018:0x4008;c->r[2]=site.tuple.dso;
        CHECK(shyt_atexit_call_v423(&list,&vm,c,c,table,1,&site,30,40) && !c->r[0]);
    }
    list.count=SHYT_ATEXIT_MAX_V423;
    CHECK(shyt_atexit_call_v423(&list,&vm,c,c,table,1,&site,30,40) && c->r[0]==UINT32_MAX);
    CHECK(list.count==SHYT_ATEXIT_MAX_V423);
    list.count=3;
}
int main(void) {
    BbCpu c={0};int code=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,8,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&c,NULL,NULL,&code)==SHYT_V393_COMPLETED && !code);
    CHECK(shyt_atexit_finalize_v423(&list,0x4008,invoke,&list));
    CHECK(n==2 && order[0]==0x4010 && order[1]==0x4000 && list.count==1);
    CHECK(shyt_atexit_finalize_v423(&list,0,invoke,&list));
    CHECK(n==3 && order[2]==0x4008 && !list.count);
    CHECK(shyt_atexit_finalize_v423(&list,0,invoke,&list) && n==3);
    list.entries[0]=(ShytDtorV423){10,0x4020,0x4008};list.count=1;
    CHECK(!shyt_atexit_finalize_v423(&list,0,invoke,&list) && n==4 && list.failed);
    CHECK(!shyt_atexit_finalize_v423(&list,0,invoke,&list) && n==4);
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V423_ATEXIT_PASS");
}
