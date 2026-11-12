/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic V389 OS-backed VM pause/reprotect/remap/map/unmap regression.
 * V381/V382 native CALL/TAIL dispatch proves no stale guest mapping.
 */
#include "native_os_vm_reconfigure_v389.h"
#include "full_cpu_abi_v194.h"
#include "native_strict_aot_v381.h"
#include "native_aot_route_v382.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#if defined(_WIN32)
#if !defined(WIN32_LEAN_AND_MEAN)
#define WIN32_LEAN_AND_MEAN 1
#endif
#include <windows.h>
#else
#include <pthread.h>
#include <sched.h>
#endif
#define CHECK(e) do {if(!(e)){fprintf(stderr,"V389_TEST_LINE_%d\n",__LINE__);return 1;}}while(0)
static ShytNativeOsVmV388 *vm_global;
static void guest_ret(BbCpu *cpu) {
    ShytNativeVmLeaseV386 lease={0};
    uint64_t value=0;
    if(!shyt_native_vm_pin_v386(&vm_global->vm,&lease))return;
    if(!shyt_native_os_vm_read_v388(vm_global,&lease,cpu->r[4],8,&value)){
        (void)shyt_native_vm_unpin_v386(&lease);
        return;
    }
    if(!shyt_native_vm_unpin_v386(&lease))return;
    cpu->r[4]+=8;cpu->rip=value;
}
static void plus(BbCpu *cpu){cpu->r[0]+=2;guest_ret(cpu);}
static void triple(BbCpu *cpu){cpu->r[0]*=3;guest_ret(cpu);}
static int attest(void *ctx,uint64_t addr,uint64_t count,uint64_t hash){
    unsigned *n=(unsigned *)ctx;
    ++*n;
    return (addr==0x400100 && count==16 && hash==0x11) ||
           (addr==0x400200 && count==32 && hash==0x22);
}
#if !defined(_WIN32)
typedef struct WorkerV389 {
    ShytNativeOsVmV388 *owner;
    _Atomic(int) acquired;
    _Atomic(int) release_now;
    int pass;
} WorkerV389;
static void *held_lease_worker(void *ctx) {
    WorkerV389 *w=(WorkerV389 *)ctx;
    ShytNativeVmLeaseV386 lease={0};
    w->pass=0;
    if(!shyt_native_vm_pin_v386(&w->owner->vm,&lease))return NULL;
    atomic_store_explicit(&w->acquired,1,memory_order_release);
    while(!atomic_load_explicit(&w->release_now,memory_order_acquire))
        sched_yield();
    w->pass=shyt_native_vm_unpin_v386(&lease);
    return NULL;
}
#endif
static int test_all(void) {
    const uint64_t stack_base=UINT64_C(0x600000000000);
    const uint64_t data_base=UINT64_C(0x40000000);
    const uint64_t new_base=UINT64_C(0x50000000);
    ShytNativeOsVmV388 owner={0};
    ShytNativeVmLeaseV386 lease={0},fresh={0};
    ShytNativeAotRouteV382 route={0};
    ShytStrictAotProofV381 proof={0};
    RcApi strict={0};
    RcFn slot_plus=NULL,slot_triple=NULL;
    RcFunction table[]={
        {0x100,16,0x11,plus,&slot_plus},
        {0x200,32,0x22,triple,&slot_triple}
    };
    unsigned checks=0;
    BbCpu cpu={0},oldcpu={0};
    uint64_t value=0;
    _Atomic(uint64_t) *before=NULL,*after=NULL;
    CHECK(!shyt_native_os_vm_pause_v389(&owner));
    CHECK(!shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_os_vm_init_v388(&owner));
    CHECK(shyt_native_os_vm_add_v388(&owner,stack_base,32,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&owner,data_base,16,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&owner));
    vm_global=&owner;
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(shyt_native_os_vm_write_v388(
        &owner,&lease,data_base,8,UINT64_C(0xDEADBEEF)));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(!shyt_native_os_vm_pause_v389(&owner)); /* live lease */
    CHECK(shyt_native_vm_unpin_v386(&lease));
#if !defined(_WIN32)
    {
        WorkerV389 w={0};
        pthread_t worker;
        w.owner=&owner;
        atomic_init(&w.acquired,0);
        atomic_init(&w.release_now,0);
        CHECK(pthread_create(&worker,NULL,held_lease_worker,&w)==0);
        while(!atomic_load_explicit(&w.acquired,memory_order_acquire))
            sched_yield();
        CHECK(!shyt_native_os_vm_pause_v389(&owner));
        atomic_store_explicit(&w.release_now,1,memory_order_release);
        CHECK(pthread_join(worker,NULL)==0 && w.pass);
    }
#endif
    CHECK(shyt_native_os_vm_pause_v389(&owner));
    CHECK(!shyt_native_os_vm_pause_v389(&owner));
    CHECK(!shyt_native_vm_pin_v386(&owner.vm,&fresh));
    CHECK(!shyt_native_os_vm_close_v388(&owner));
    CHECK(!shyt_native_os_vm_reprotect_v389(&owner,data_base,0));
    CHECK(!shyt_native_os_vm_reprotect_v389(&owner,data_base,
        SHYT_V386_WRITE|SHYT_V386_EXECUTE));
    CHECK(!shyt_native_os_vm_reprotect_v389(&owner,0xBAD,
        SHYT_V386_READ));
    CHECK(shyt_native_os_vm_reprotect_v389(&owner,data_base,
        SHYT_V386_READ));
#if defined(_WIN32)
    {
        MEMORY_BASIC_INFORMATION info={0};
        CHECK(VirtualQuery(owner.allocations[1].words,
                           &info,sizeof(info))==sizeof(info));
        CHECK(info.Protect==PAGE_READONLY);
    }
#endif
    CHECK(shyt_native_os_vm_resume_v389(&owner));
    CHECK(!shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(!shyt_native_os_vm_write_v388(
        &owner,&lease,data_base,8,0xAAAA));
    CHECK(shyt_native_os_vm_read_v388(
        &owner,&lease,data_base,8,&value));
    CHECK(value==UINT64_C(0xDEADBEEF));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!shyt_native_os_vm_remap_v389(&owner,data_base,1));
    CHECK(!shyt_native_os_vm_reprotect_v389(
        &owner,data_base,SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_pause_v389(&owner));
    CHECK(shyt_native_os_vm_reprotect_v389(&owner,data_base,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(!shyt_native_os_vm_remap_v389(&owner,data_base,2));
    before=owner.allocations[1].words;
    CHECK(shyt_native_os_vm_remap_v389(&owner,data_base,1));
    after=owner.allocations[1].words;
    CHECK(after && after!=before); /* old page was live at new allocate */
    CHECK(owner.vm.regions[0].words==after);
    CHECK(shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(shyt_native_os_vm_read_v388(
        &owner,&lease,data_base,8,&value));
    CHECK(value==UINT64_C(0xDEADBEEF));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(shyt_native_os_vm_pause_v389(&owner));
    CHECK(shyt_native_os_vm_remap_v389(&owner,data_base,0));
    CHECK(shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(shyt_native_os_vm_read_v388(
        &owner,&lease,data_base,8,&value));
    CHECK(value==0);
    CHECK(shyt_native_vm_unpin_v386(&lease));
    /* Dynamically add and remove a genuine OS-backed region. */
    CHECK(!shyt_native_os_vm_map_v389(
        &owner,new_base,8,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_pause_v389(&owner));
    CHECK(!shyt_native_os_vm_map_v389(
        &owner,data_base+8,8,SHYT_V386_READ)); /* overlap */
    CHECK(!shyt_native_os_vm_map_v389(
        &owner,new_base,8,SHYT_V386_WRITE|SHYT_V386_EXECUTE));
    CHECK(shyt_native_os_vm_map_v389(
        &owner,new_base,8,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(owner.vm.region_count==3 && owner.allocation_count==3);
    CHECK(owner.vm.regions[0].guest_base==data_base);
    CHECK(owner.vm.regions[1].guest_base==new_base);
    CHECK(owner.vm.regions[2].guest_base==stack_base);
    CHECK(!shyt_native_os_vm_map_v389(
        &owner,new_base,8,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(shyt_native_os_vm_write_v388(
        &owner,&lease,new_base,8,0xFEED));
    CHECK(shyt_native_os_vm_read_v388(
        &owner,&lease,new_base,8,&value) && value==0xFEED);
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(shyt_native_os_vm_pause_v389(&owner));
    CHECK(shyt_native_os_vm_unmap_v389(&owner,new_base));
    CHECK(!shyt_native_os_vm_unmap_v389(&owner,new_base));
    CHECK(owner.vm.region_count==2 && owner.allocation_count==2);
    CHECK(shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(!shyt_native_os_vm_read_v388(
        &owner,&lease,new_base,8,&value));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    /* Original guest base can be mapped again after removing old pages. */
    CHECK(shyt_native_os_vm_pause_v389(&owner));
    CHECK(shyt_native_os_vm_map_v389(
        &owner,new_base,8,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_resume_v389(&owner));
    CHECK(shyt_native_vm_pin_v386(&owner.vm,&lease));
    CHECK(shyt_native_os_vm_read_v388(
        &owner,&lease,new_base,8,&value) && value==0);
    CHECK(!shyt_native_os_vm_write_v388(
        &owner,&lease,new_base,8,0xBAD));
    CHECK(shyt_native_vm_unpin_v386(&lease));

    /* New host pages have not changed the logical guest stack; the
     * native-only compiled function dispatch still returns correctly. */
    CHECK(shyt_strict_aot_base_v381(&strict,0x400000));
    CHECK(shyt_strict_aot_activate_v381(&strict,table,2,0x400000,
        attest,&checks,&proof));
    CHECK(checks==2);
    CHECK(shyt_native_aot_prepare_v382(
        &route,&strict,table,2,&proof,
        shyt_native_os_vm_stack_write_v388,&owner));
    cpu.r[0]=5;cpu.r[4]=stack_base+24*8;
    oldcpu=cpu;
    CHECK(!shyt_native_aot_try_call_v382(
        &route,&cpu,0x400999,0x12));
    CHECK(!memcmp(&oldcpu,&cpu,sizeof(cpu)));
    CHECK(shyt_native_aot_try_call_v382(
        &route,&cpu,0x400100,0x1234));
    CHECK(cpu.r[0]==7 && cpu.rip==0x1234);
    CHECK(cpu.r[4]==stack_base+24*8);
    CHECK(shyt_native_os_vm_stack_write_v388(
        &owner,stack_base+24*8,0x5678));
    cpu.rip=0x400200;
    CHECK(shyt_native_aot_try_tail_v382(&route,&cpu));
    CHECK(cpu.r[0]==21 && cpu.rip==0x5678);
    CHECK(shyt_native_aot_dispose_v382(&route)); /* UNPUBLISHED */
    vm_global=NULL;
    CHECK(shyt_native_os_vm_close_v388(&owner));
    CHECK(!shyt_native_os_vm_pause_v389(&owner));
    CHECK(!shyt_native_os_vm_release_v388(&owner,0));
    CHECK(shyt_native_os_vm_release_v388(&owner,1));
    CHECK(owner.released && owner.vm.region_count==3);
    CHECK(!shyt_native_os_vm_resume_v389(&owner));
    CHECK(!shyt_native_os_vm_map_v389(&owner,0x70000000,8,
        SHYT_V386_READ));
    return 0;
}
int main(void){
    CHECK(!test_all());
    puts("NATIVE_V389_QUIESCENT_OS_REMAP_PERMISSIONS_AOT_CALL_TAIL_PASS");
    return 0;
}
