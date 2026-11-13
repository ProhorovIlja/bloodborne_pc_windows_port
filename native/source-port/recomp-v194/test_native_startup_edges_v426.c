/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_memcmp_v418.h"
#include "native_startup_edges_v426.h"
#include <stdlib.h>
#include <stdio.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V418_FAIL %d\n",__LINE__);abort();} }while(0)
static ShytNativeOsVmV388 vm;
static void good(BbCpu *cpu) {
    uint64_t word=0;
    CHECK(cpu->rip==11 && cpu->r[4]==0x4008);
    CHECK(shyt_generated_try_load_v390(cpu->r[4],8,&word) && word==12);
    cpu->rip=word;
    cpu->r[4]+=8;
}
static void bad(BbCpu *cpu) { (void)cpu; }
static void body(BbCpu *cpu) {
    const RcFunction registry[]={{.offset=11,.fn=good},{.offset=21,.fn=bad}};
    const ShytStartupEdgeV418 approved={11,12}, corrupt={21,22}, missing={31,32};
    const ShytMemcmpSiteV418 compare={{51,52},0x4000,0x4028,16};
    const ShytStartupEdgeV418 rows[]={{11,12},{21,12},{21,22}};
    const ShytStartupEdgeV418 invalid[]={{11,12},{11,12}};
    ShytStartupEdgesV426 plan={0};
    CHECK(!shyt_startup_edges_init_v426(&plan,invalid,2,registry,2));
    CHECK(!shyt_startup_edges_init_v426(&plan,&missing,1,registry,2));
    CHECK(!plan.edges && !plan.n);
    CHECK(shyt_startup_edges_init_v426(&plan,rows,3,registry,2));
    CHECK(!shyt_startup_edges_init_v426(&plan,rows,3,registry,2));
    CHECK(shyt_startup_edge_v426(&plan,11,12)==&rows[0]);
    CHECK(shyt_startup_edge_v426(&plan,21,12)==&rows[1]);
    CHECK(shyt_startup_edge_v426(&plan,21,22)==&rows[2]);
    CHECK(!shyt_startup_edge_v426(&plan,11,22));
    CHECK(!shyt_startup_edge_v426(&plan,11,13));
    cpu->r[4]=0x4010;
    CHECK(shyt_startup_call_v418(&vm,cpu,cpu,registry,2,&approved,11,13,0x4000,0x4010)==SHYT_STARTUP_DENIED);
    CHECK(shyt_startup_call_v418(&vm,cpu,cpu,registry,2,&approved,11,12,0x4009,0x4018)==SHYT_STARTUP_DENIED);
    CHECK(shyt_startup_call_v418(&vm,cpu,cpu,registry,2,&missing,31,32,0x4000,0x4010)==SHYT_STARTUP_DENIED);
    CHECK(cpu->rip==0 && cpu->r[4]==0x4010);
    CHECK(shyt_startup_call_v418(&vm,cpu,cpu,registry,2,shyt_startup_edge_v426(&plan,11,12),11,12,0x4000,0x4010)==SHYT_STARTUP_RETURNED);
    CHECK(shyt_startup_call_v418(&vm,cpu,cpu,registry,2,&corrupt,21,22,0x4000,0x4010)==SHYT_STARTUP_BAD_RETURN);
    CHECK(shyt_generated_try_store_v390(0x4000,8,0x80));
    CHECK(shyt_generated_try_store_v390(0x4010,8,0xff));
    cpu->r[7]=0x4000; cpu->r[6]=0x4010; cpu->r[2]=8;
    CHECK(shyt_memcmp_v418(&vm,cpu,cpu,&compare,51,52) && cpu->r[0]==UINT32_C(0xffffff81));
    cpu->r[2]=0;
    CHECK(shyt_memcmp_v418(&vm,cpu,cpu,&compare,51,52) && !cpu->r[0]);
    cpu->r[6]=0x401f;cpu->r[2]=2;
    CHECK(!shyt_memcmp_v418(&vm,cpu,cpu,&compare,51,52) && !cpu->r[0] && cpu->rip==52);
    cpu->r[2]=17;
    CHECK(!shyt_memcmp_v418(&vm,cpu,cpu,&compare,51,52));
}
int main(void) {
    BbCpu cpu={0}; int code=-1;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(&vm,0x4000,4,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(shyt_generated_call_recoverable_v393(&vm,body,&cpu,NULL,NULL,&code)==SHYT_V393_COMPLETED);
    CHECK(!code && shyt_native_os_vm_close_v388(&vm) && shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V426_INDEXED_EDGES_PASS");
    return 0;
}
