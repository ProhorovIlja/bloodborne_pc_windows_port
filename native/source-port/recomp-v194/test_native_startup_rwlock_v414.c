/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "native_startup_rwlock_v414.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V414_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static ShytStartupRwlockV414 rw;
static const uint64_t addr=0x400000u;
static void exercise(BbCpu *cpu) {
    const ShytRwSiteV414 init={1,2,addr,SHYT_RW_INIT};
    const ShytRwSiteV414 write={3,4,addr,SHYT_RW_WRITE};
    const ShytRwSiteV414 unlock={5,6,addr,SHYT_RW_UNLOCK};
    uint64_t word=0;
    cpu->r[7]=addr;
    cpu->r[4]=addr;
    CHECK(shyt_rw_call_v414(&rw,&vm,&init,cpu,cpu,1,2) && cpu->r[0] && !rw.live);
    cpu->r[4]=addr+8;
    CHECK(!shyt_rw_call_v414(&rw,&vm,&init,cpu,cpu,1,4));
    cpu->r[6]=1;
    CHECK(shyt_rw_call_v414(&rw,&vm,&init,cpu,cpu,1,2) && cpu->r[0] && !rw.live);
    cpu->r[6]=0;
    CHECK(shyt_rw_call_v414(&rw,&vm,&init,cpu,cpu,1,2) && !cpu->r[0] && cpu->rip==2);
    CHECK(shyt_generated_try_load_v390(addr,8,&word) && word==SHYT_RW_TOKEN_V414);
    CHECK(shyt_rw_call_v414(&rw,&vm,&unlock,cpu,cpu,5,6) && cpu->r[0]);
    CHECK(shyt_generated_try_store_v390(addr,8,0));
    CHECK(shyt_rw_call_v414(&rw,&vm,&write,cpu,cpu,3,4) && cpu->r[0] && !rw.held);
    CHECK(shyt_generated_try_store_v390(addr,8,word));
    CHECK(shyt_rw_call_v414(&rw,&vm,&write,cpu,cpu,3,4) && !cpu->r[0] && rw.held);
    CHECK(!shyt_rw_destroy_v414(&rw));
    CHECK(shyt_rw_call_v414(&rw,&vm,&write,cpu,cpu,3,4) && cpu->r[0] && rw.held);
    CHECK(shyt_rw_call_v414(&rw,&vm,&unlock,cpu,cpu,5,6) && !cpu->r[0] && !rw.held);
}
int main(void) {
    BbCpu cpu={0};int code=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,addr,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(shyt_generated_call_recoverable_v393(&vm,exercise,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && !shyt_generated_active_v390() && shyt_rw_destroy_v414(&rw));
    CHECK(shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V414_RWLOCK_IMPORT_PASS");
    return 0;
}
