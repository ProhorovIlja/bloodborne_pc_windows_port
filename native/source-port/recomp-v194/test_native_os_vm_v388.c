/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original-free OS VirtualAlloc/mmap backed multi-region, cross-word
 * memory, guest permissions and native-only RcApi CALL/TAIL tests.
 */
#include "native_os_vm_v388.h"
#include "full_cpu_abi_v194.h"
#include "native_aot_route_v382.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#if !defined(_WIN32)
#include <pthread.h>
#endif
#define CHECK(cond) do { if(!(cond)) { \
    fprintf(stderr,"NATIVE_V388_ASSERT_LINE_%d\n",__LINE__);return 1; \
} } while(0)
static ShytNativeOsVmV388 *active_vm_v388;
static void native_return_v388(BbCpu *cpu) {
    ShytNativeVmLeaseV386 lease={0};
    uint64_t value=0;
    if (!shyt_native_vm_pin_v386(&active_vm_v388->vm,&lease))return;
    if (!shyt_native_os_vm_read_v388(active_vm_v388,&lease,cpu->r[4],8,&value)){
        (void)shyt_native_vm_unpin_v386(&lease);return;
    }
    if (!shyt_native_vm_unpin_v386(&lease))return;
    cpu->r[4]+=8;
    cpu->rip=value;
}
static void native_plus_v388(BbCpu *cpu){cpu->r[0]+=5;native_return_v388(cpu);}
static void native_times_v388(BbCpu *cpu){cpu->r[0]*=2;native_return_v388(cpu);}
static int attest_v388(void *ctx,uint64_t addr,uint64_t size,uint64_t hash){
    unsigned *n=(unsigned*)ctx;
    ++*n;
    return (addr==UINT64_C(0x400100) && size==16 && hash==0x11) ||
           (addr==UINT64_C(0x400200) && size==32 && hash==0x22);
}
#if !defined(_WIN32)
typedef struct ThreadV388 {
    ShytNativeOsVmV388 *owner;
    uint64_t target;
    unsigned value;
    int ok;
} ThreadV388;
static void *writer_v388(void *arg){
    ThreadV388 *t=(ThreadV388 *)arg;
    ShytNativeVmLeaseV386 lease={0};
    t->ok=0;
    if(!shyt_native_vm_pin_v386(&t->owner->vm,&lease))return NULL;
    for(unsigned i=0;i<10000;i++)
        if(!shyt_native_os_vm_write_v388(
              t->owner,&lease,t->target,1,t->value)){
            (void)shyt_native_vm_unpin_v386(&lease);
            return NULL;
        }
    t->ok=shyt_native_vm_unpin_v386(&lease);
    return NULL;
}
#endif
static int run(void) {
    const uint64_t base=UINT64_C(0x600000000000);
    const uint64_t read_base=UINT64_C(0x40000000);
    const uint64_t write_base=UINT64_C(0x50000000);
    const uint64_t adjacent=base+16*8;
    ShytNativeOsVmV388 o={0},notready={0};
    ShytNativeVmLeaseV386 lease={0},other={0},fresh={0};
    RcApi strict={0};
    RcFn plus=NULL,times=NULL;
    RcFunction table[]={
        {0x100,16,0x11,native_plus_v388,&plus},
        {0x200,32,0x22,native_times_v388,&times}
    };
    ShytStrictAotProofV381 proof={0};
    ShytNativeAotRouteV382 route={0};
    unsigned attest_count=0;
    BbCpu cpu={0},before;
    uint64_t value=0,unchanged;
    CHECK(!shyt_native_os_vm_add_v388(
        &notready,base,16,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(!shyt_native_os_vm_seal_v388(&notready));
    CHECK(!shyt_native_os_vm_release_v388(&notready,1));
    CHECK(shyt_native_os_vm_init_v388(&o));
    CHECK(!shyt_native_os_vm_init_v388(&o));
    CHECK(o.page_size>=4096 && (o.page_size&(o.page_size-1u))==0);
    CHECK(!shyt_native_os_vm_add_v388(&o,base,0,SHYT_V386_READ));
    CHECK(!shyt_native_os_vm_add_v388(&o,base,16,0));
    CHECK(!shyt_native_os_vm_add_v388(&o,base,16,
                SHYT_V386_WRITE|SHYT_V386_EXECUTE));
    CHECK(!shyt_native_os_vm_add_v388(&o,UINT64_MAX-7,16,
                SHYT_V386_READ|SHYT_V386_WRITE));
    /* Insert addresses deliberately out of guest-address order. */
    CHECK(shyt_native_os_vm_add_v388(
        &o,base,16,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(!shyt_native_os_vm_add_v388(
        &o,base+8,16,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_add_v388(
        &o,read_base,8,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_add_v388(
        &o,write_base,8,SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(
        &o,adjacent,8,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(o.vm.region_count==4 && o.allocation_count==4);
    CHECK(o.vm.regions[0].guest_base==read_base);
    CHECK(o.vm.regions[1].guest_base==write_base);
    CHECK(o.vm.regions[2].guest_base==base);
    CHECK(o.vm.regions[3].guest_base==adjacent);
    for(size_t i=0;i<o.allocation_count;i++){
        CHECK(o.allocations[i].live && o.allocations[i].words);
        CHECK(((uintptr_t)o.allocations[i].words%o.page_size)==0);
        CHECK(o.allocations[i].reserved_bytes%o.page_size==0);
    }
    CHECK(shyt_native_os_vm_seal_v388(&o));
    CHECK(!shyt_native_os_vm_add_v388(
        &o,0x80000000,8,SHYT_V386_READ));
    CHECK(!shyt_native_os_vm_seal_v388(&o));
    CHECK(shyt_native_os_vm_mapping_v388(&o)==&o.vm);
    CHECK(shyt_native_vm_pin_v386(&o.vm,&lease));
    CHECK(!shyt_native_os_vm_probe_v388(
        &o,&lease,read_base,8,SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_probe_v388(
        &o,&lease,read_base,8,SHYT_V386_READ));
    CHECK(!shyt_native_os_vm_write_v388(
        &o,&lease,read_base,8,UINT64_MAX));
    CHECK(shyt_native_os_vm_read_v388(
        &o,&lease,read_base,8,&value));
    CHECK(value==0);
    CHECK(shyt_native_os_vm_write_v388(
        &o,&lease,write_base,8,UINT64_C(0x88)));
    CHECK(!shyt_native_os_vm_read_v388(
        &o,&lease,write_base,8,&value));
    CHECK(!shyt_native_os_vm_probe_v388(
        &o,&lease,base+15*8+7,2,SHYT_V386_WRITE));
    CHECK(!shyt_native_os_vm_write_v388(
        &o,&lease,base+15*8+7,2,0xABCD));
    CHECK(shyt_native_os_vm_write_v388(
        &o,&lease,base,8,UINT64_C(0x1122334455667788)));
    CHECK(shyt_native_os_vm_write_v388(
        &o,&lease,base+8,8,UINT64_C(0x99AABBCCDDEEFF00)));
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+7,2,&value));
    CHECK(value==UINT64_C(0x0011));
    CHECK(shyt_native_os_vm_write_v388(&o,&lease,base+7,2,0xCDEF));
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+7,2,&value));
    CHECK(value==0xCDEF);
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base,8,&value));
    CHECK(value==UINT64_C(0xEF22334455667788));
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+8,8,&value));
    CHECK(value==UINT64_C(0x99AABBCCDDEE00CD));
    /* Unaligned cross-word 8-byte access: two atomics, not one. */
    CHECK(shyt_native_os_vm_write_v388(
        &o,&lease,base+3,8,UINT64_C(0x0102030405060708)));
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+3,8,&value));
    CHECK(value==UINT64_C(0x0102030405060708));
    /* Multiple OS regions may be adjacent but a single operation
     * may NEVER straddle two independent mappings. */
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+15*8,8,&value));
    unchanged=value;
    CHECK(!shyt_native_os_vm_write_v388(
        &o,&lease,base+16*8-1,2,0xBEEF));
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+15*8,&value));
    CHECK(value==unchanged);
    CHECK(!shyt_native_os_vm_write_v388(
        &o,&lease,base+6,3,0xDEAD)); /* width 3 unsupported */
    CHECK(!shyt_native_os_vm_read_v388(
        &o,&lease,UINT64_MAX,8,&value));
    CHECK(!shyt_native_os_vm_read_v388(&o,&lease,base,8,NULL));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!shyt_native_os_vm_write_v388(
        &o,&lease,base,8,0xBAD));
#if !defined(_WIN32)
    ThreadV388 a={&o,base+32,0xAA,0},b={&o,base+33,0xBB,0};
    pthread_t ta,tb;
    CHECK(pthread_create(&ta,NULL,writer_v388,&a)==0);
    CHECK(pthread_create(&tb,NULL,writer_v388,&b)==0);
    CHECK(pthread_join(ta,NULL)==0);
    CHECK(pthread_join(tb,NULL)==0);
    CHECK(a.ok && b.ok);
    CHECK(shyt_native_vm_pin_v386(&o.vm,&lease));
    CHECK(shyt_native_os_vm_read_v388(&o,&lease,base+32,2,&value));
    CHECK(value==0xBBAA); /* same atomic word, no lost updates */
    CHECK(shyt_native_vm_unpin_v386(&lease));
#endif
    CHECK(shyt_strict_aot_base_v381(&strict,0x400000));
    CHECK(shyt_strict_aot_activate_v381(
        &strict,table,2,0x400000,attest_v388,&attest_count,&proof));
    CHECK(attest_count==2);
    CHECK(shyt_native_aot_prepare_v382(
        &route,&strict,table,2,&proof,
        shyt_native_os_vm_stack_write_v388,&o));
    active_vm_v388=&o;
    cpu.r[0]=10;
    cpu.r[4]=base+12*8;
    before=cpu;
    CHECK(!shyt_native_aot_try_call_v382(
        &route,&cpu,0x400999,0xAAA1));
    CHECK(memcmp(&before,&cpu,sizeof(cpu))==0);
    CHECK(shyt_native_aot_try_call_v382(
        &route,&cpu,0x400100,0xAAA1));
    CHECK(cpu.r[0]==15 && cpu.rip==0xAAA1);
    CHECK(cpu.r[4]==base+12*8);
    CHECK(shyt_native_vm_pin_v386(&o.vm,&lease));
    CHECK(shyt_native_os_vm_read_v388(
        &o,&lease,base+11*8,8,&value));
    CHECK(value==0xAAA1);
    CHECK(shyt_native_os_vm_write_v388(
        &o,&lease,base+12*8,8,0xAAA2));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    cpu.rip=0x400200;
    CHECK(shyt_native_aot_try_tail_v382(&route,&cpu));
    CHECK(cpu.r[0]==30 && cpu.rip==0xAAA2);
    CHECK(cpu.r[4]==base+13*8);
    /* Lifecycle: released only after close, quiescence and join. */
    CHECK(!shyt_native_os_vm_release_v388(&o,1));
    CHECK(shyt_native_vm_pin_v386(&o.vm,&lease));
    CHECK(shyt_native_vm_pin_v386(&o.vm,&other));
    CHECK(shyt_native_os_vm_close_v388(&o));
    CHECK(!shyt_native_os_vm_release_v388(&o,1));
    CHECK(!shyt_native_vm_pin_v386(&o.vm,&fresh));
    CHECK(!shyt_native_os_vm_stack_write_v388(&o,base,5));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!shyt_native_vm_quiescent_v386(&o.vm));
    CHECK(shyt_native_vm_unpin_v386(&other));
    CHECK(shyt_native_vm_quiescent_v386(&o.vm));
    CHECK(!shyt_native_os_vm_release_v388(&o,0));
    /* This route is UNPUBLISHED and no worker is running. */
    CHECK(shyt_native_aot_dispose_v382(&route));
    active_vm_v388=NULL;
    CHECK(shyt_native_os_vm_release_v388(&o,1));
    CHECK(o.released);
    CHECK(!shyt_native_os_vm_mapping_v388(&o));
    CHECK(!shyt_native_os_vm_release_v388(&o,1));
    CHECK(!shyt_native_vm_pin_v386(&o.vm,&fresh));
    return 0;
}
int main(void) {
    CHECK(!run());
    puts("NATIVE_V388_OS_PAGES_CROSS_WORD_PERMISSIONED_AOT_CALL_TAIL_PASS");
    return 0;
}
