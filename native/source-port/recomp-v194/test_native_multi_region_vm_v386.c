/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic multi-region guest memory + real V381/V382 native-only
 * RcApi CALL/TAIL ABI. No original Bloodborne files or game startup.
 */
#include "full_cpu_abi_v194.h"
#include "native_strict_aot_v381.h"
#include "native_aot_route_v382.h"
#include "native_multi_region_vm_v386.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#if !defined(_WIN32)
#include <pthread.h>
#endif
#define CHECK(x) do {if(!(x)){fprintf(stderr,"NATIVE_V386_LINE_%d\n",__LINE__);return 1;}}while(0)
static ShytNativeVmV386 *active_vm;
static void native_return(BbCpu *cpu) {
    ShytNativeVmLeaseV386 lease={0};
    uint64_t next=0;
    if (!shyt_native_vm_pin_v386(active_vm,&lease))return;
    if (!shyt_native_vm_read_v386(&lease,cpu->r[4],8,&next)) {
        (void)shyt_native_vm_unpin_v386(&lease);
        return;
    }
    if (!shyt_native_vm_unpin_v386(&lease))return;
    cpu->r[4]+=8;
    cpu->rip=next;
}
static void synthetic_plus(BbCpu *cpu){cpu->r[0]+=5;native_return(cpu);}
static void synthetic_double(BbCpu *cpu){cpu->r[0]*=2;native_return(cpu);}
static int attester(void *ctx,uint64_t at,uint64_t size,uint64_t hash) {
    unsigned *seen=(unsigned *)ctx;
    (*seen)++;
    return (at==0x400100 && size==16 && hash==0x111) ||
           (at==0x400200 && size==32 && hash==0x222);
}
#if !defined(_WIN32)
typedef struct ThreadData {
    ShytNativeVmV386 *vm;
    uint64_t addr;
    unsigned byte;
    int good;
} ThreadData;
static void *byte_writer(void *ctx){
    ThreadData *a=(ThreadData *)ctx;
    ShytNativeVmLeaseV386 lease={0};
    a->good=0;
    if(!shyt_native_vm_pin_v386(a->vm,&lease))return NULL;
    for(unsigned i=0;i<10000;i++)
        if(!shyt_native_vm_write_v386(&lease,a->addr,1,a->byte)) {
            (void)shyt_native_vm_unpin_v386(&lease);
            return NULL;
        }
    a->good=shyt_native_vm_unpin_v386(&lease);
    return NULL;
}
#endif
static int test_vm(void) {
    const uint64_t stackbase=UINT64_C(0x600000000000);
    const uint64_t database=UINT64_C(0x40000000);
    const uint64_t rob=UINT64_C(0x30000000);
    const uint64_t wob=UINT64_C(0x50000000);
    _Atomic(uint64_t) stackmem[32],readmem[8],writemem[8],datamem[16];
    ShytNativeVmV386 vm={0};
    ShytNativeVmLeaseV386 lease={0},other={0};
    uint64_t result=0;
    for(size_t i=0;i<32;i++)atomic_init(&stackmem[i],0);
    for(size_t i=0;i<8;i++){
        atomic_init(&readmem[i],UINT64_C(0xAA));
        atomic_init(&writemem[i],0);
    }
    for(size_t i=0;i<16;i++)atomic_init(&datamem[i],0);
    CHECK(!shyt_native_vm_seal_v386(&vm));
    CHECK(!shyt_native_vm_pin_v386(&vm,&lease));
    CHECK(!shyt_native_vm_add_region_v386(&vm,0,stackmem,32,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase+1,stackmem,32,
        SHYT_V386_READ));
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase,stackmem,0,
        SHYT_V386_READ));
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase,stackmem,32,0));
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase,stackmem,32,8));
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase,stackmem,32,
        SHYT_V386_WRITE|SHYT_V386_EXECUTE));
    CHECK(!shyt_native_vm_add_region_v386(&vm,UINT64_MAX-7,stackmem,32,
        SHYT_V386_READ));
    CHECK(shyt_native_vm_add_region_v386(&vm,stackbase,stackmem,32,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase+8,readmem,8,
        SHYT_V386_READ)); /* guest overlap */
    CHECK(!shyt_native_vm_add_region_v386(&vm,stackbase+0x2000,stackmem,32,
        SHYT_V386_READ)); /* host memory alias */
    CHECK(shyt_native_vm_add_region_v386(&vm,rob,readmem,8,
        SHYT_V386_READ));
    CHECK(shyt_native_vm_add_region_v386(&vm,database,datamem,16,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_vm_add_region_v386(&vm,wob,writemem,8,
        SHYT_V386_WRITE));
    CHECK(vm.region_count==4);
    CHECK(vm.regions[0].guest_base==rob);
    CHECK(vm.regions[1].guest_base==database);
    CHECK(vm.regions[2].guest_base==wob);
    CHECK(vm.regions[3].guest_base==stackbase);
    CHECK(shyt_native_vm_seal_v386(&vm));
    CHECK(!shyt_native_vm_seal_v386(&vm));
    CHECK(!shyt_native_vm_add_region_v386(&vm,0x700000,readmem,8,
        SHYT_V386_READ));
    CHECK(shyt_native_vm_pin_v386(&vm,&lease));
    CHECK(!shyt_native_vm_pin_v386(&vm,&lease));
    CHECK(shyt_native_vm_probe_v386(&lease,stackbase+8*31,8,
        SHYT_V386_WRITE));
    CHECK(!shyt_native_vm_probe_v386(&lease,stackbase+8*31+1,8,
        SHYT_V386_WRITE));
    CHECK(shyt_native_vm_write_v386(&lease,stackbase+8*31,8,0xABCDEF));
    CHECK(shyt_native_vm_read_v386(&lease,stackbase+8*31,8,&result));
    CHECK(result==0xABCDEF);
    CHECK(!shyt_native_vm_read_v386(&lease,stackbase+8*32,8,&result));
    CHECK(!shyt_native_vm_write_v386(&lease,stackbase+8*32,8,0xBAD));
    CHECK(!shyt_native_vm_write_v386(&lease,stackbase+1,8,0xBAD));
    CHECK(!shyt_native_vm_write_v386(&lease,stackbase+7,2,0xBAD));
    CHECK(!shyt_native_vm_write_v386(&lease,stackbase,3,0xBAD));
    CHECK(!shyt_native_vm_read_v386(&lease,rob+64,1,&result));
    CHECK(!shyt_native_vm_write_v386(&lease,rob,8,0xBAD));
    CHECK(shyt_native_vm_read_v386(&lease,rob,8,&result));
    CHECK(result==0xAA);
    CHECK(shyt_native_vm_write_v386(&lease,wob,8,0x123456));
    CHECK(!shyt_native_vm_read_v386(&lease,wob,8,&result));
    CHECK(atomic_load(&writemem[0])==0x123456);
    CHECK(shyt_native_vm_write_v386(&lease,database,8,
        UINT64_C(0x8877665544332211)));
    CHECK(shyt_native_vm_read_v386(&lease,database+1,2,&result));
    CHECK(result==UINT64_C(0x3322));
    CHECK(shyt_native_vm_write_v386(&lease,database+2,4,
        UINT32_C(0xAABBCCDD)));
    CHECK(shyt_native_vm_read_v386(&lease,database,8,&result));
    CHECK(result==UINT64_C(0x8877AABBCCDD2211));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!shyt_native_vm_unpin_v386(&lease));
#if !defined(_WIN32)
    ThreadData a={&vm,database+16,0x11,0},b={&vm,database+17,0x22,0};
    pthread_t ta,tb;
    CHECK(pthread_create(&ta,NULL,byte_writer,&a)==0);
    CHECK(pthread_create(&tb,NULL,byte_writer,&b)==0);
    CHECK(pthread_join(ta,NULL)==0);
    CHECK(pthread_join(tb,NULL)==0);
    CHECK(a.good && b.good);
    CHECK(shyt_native_vm_pin_v386(&vm,&lease));
    CHECK(shyt_native_vm_read_v386(&lease,database+16,2,&result));
    CHECK(result==0x2211);
    CHECK(shyt_native_vm_unpin_v386(&lease));
#endif
    CHECK(shyt_native_vm_stack_write_v386(&vm,stackbase+24*8,0xCAFEBABE));
    CHECK(atomic_load(&stackmem[24])==0xCAFEBABE);
    CHECK(!shyt_native_vm_stack_write_v386(&vm,rob,0xBAD));
    CHECK(!shyt_native_vm_stack_write_v386(&vm,stackbase-8,0xBAD));
    CHECK(shyt_native_vm_pin_v386(&vm,&lease));
    CHECK(shyt_native_vm_pin_v386(&vm,&other));
    CHECK(shyt_native_vm_close_v386(&vm));
    CHECK(!shyt_native_vm_quiescent_v386(&vm));
    ShytNativeVmLeaseV386 fresh={0};
    CHECK(!shyt_native_vm_pin_v386(&vm,&fresh));
    CHECK(!shyt_native_vm_stack_write_v386(&vm,stackbase,0));
    /* Existing pins remain legitimate until drained and workers joined. */
    CHECK(shyt_native_vm_read_v386(&lease,rob,8,&result));
    CHECK(result==0xAA);
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!shyt_native_vm_quiescent_v386(&vm));
    CHECK(shyt_native_vm_unpin_v386(&other));
    CHECK(shyt_native_vm_quiescent_v386(&vm));
    return 0;
}
static int test_native_dispatch(void) {
    ShytNativeVmV386 vm={0};
    ShytNativeVmLeaseV386 lease={0};
    _Atomic(uint64_t) words[16];
    RcApi strict={0};
    RcFn slot_a=NULL,slot_b=NULL;
    RcFunction fn[]={
        {0x100,16,0x111,synthetic_plus,&slot_a},
        {0x200,32,0x222,synthetic_double,&slot_b}
    };
    ShytStrictAotProofV381 proof={0};
    ShytNativeAotRouteV382 route={0};
    BbCpu cpu={0},before;
    unsigned calls=0;
    uint64_t value=0;
    const uint64_t base=UINT64_C(0x600000000000);
    for(size_t i=0;i<16;i++)atomic_init(&words[i],0);
    CHECK(shyt_native_vm_add_region_v386(
        &vm,base,words,16,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_vm_seal_v386(&vm));
    CHECK(shyt_strict_aot_base_v381(&strict,0x400000));
    CHECK(shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
        attester,&calls,&proof));
    CHECK(calls==2);
    CHECK(shyt_native_aot_prepare_v382(&route,&strict,fn,2,&proof,
        shyt_native_vm_stack_write_v386,&vm));
    active_vm=&vm;
    cpu.r[0]=10;
    cpu.r[4]=base+12*8;
    before=cpu;
    CHECK(!shyt_native_aot_try_call_v382(&route,&cpu,0x400999,0xABCD));
    CHECK(!memcmp(&cpu,&before,sizeof cpu));
    CHECK(shyt_native_aot_try_call_v382(&route,&cpu,0x400100,0xABCD));
    CHECK(cpu.r[0]==15 && cpu.rip==0xABCD);
    CHECK(cpu.r[4]==base+12*8);
    CHECK(shyt_native_vm_pin_v386(&vm,&lease));
    CHECK(shyt_native_vm_read_v386(&lease,base+11*8,8,&value));
    CHECK(value==0xABCD);
    CHECK(shyt_native_vm_write_v386(&lease,base+12*8,8,0xF00D));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    cpu.rip=0x400200;
    CHECK(shyt_native_aot_try_tail_v382(&route,&cpu));
    CHECK(cpu.r[0]==30 && cpu.rip==0xF00D);
    CHECK(cpu.r[4]==base+13*8);
    CHECK(shyt_native_vm_close_v386(&vm));
    before=cpu;cpu.r[4]=base+12*8;
    CHECK(!shyt_native_aot_try_call_v382(&route,&cpu,0x400100,0xCAFE));
    CHECK(cpu.r[4]==base+12*8 && cpu.rip==before.rip);
    CHECK(shyt_native_vm_quiescent_v386(&vm));
    CHECK(shyt_native_aot_dispose_v382(&route)); /* never published */
    return 0;
}
int main(void){
    CHECK(!test_vm());
    CHECK(!test_native_dispatch());
    puts("NATIVE_V386_MULTI_REGION_PERMISSIONS_AOT_CALL_TAIL_PASS");
    return 0;
}
