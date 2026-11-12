/* SPDX-License-Identifier: GPL-2.0-or-later
 * V388: real OS page allocations back the V386 guest region map
 * for V245/V384/V387 Win64 AOT+25 import integration tests.
 * No original retail game code or independent game boot.
 */
#include "native_unified_import_v387.h"
#include "native_os_vm_v388.h"
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN 1
#include <windows.h>
#endif
/* The real pinned upstream V245 public header already defines BbCpu.
 * V194's standalone mirror cannot be included in that same C TU. */
#include <stddef.h>
_Static_assert(sizeof(BbCpu)==840 && offsetof(BbCpu,rip)==128,
               "pinned upstream BbCpu layout changed");
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V388_OS_CHAIN_LINE_%d\n",__LINE__);return 1;}}while(0)
#if defined(_WIN32)
typedef struct {
    uint64_t begin,end;
    unsigned pins,unpins;
} GuestRawWindow;
static ShytNativeVmV386 *native_vm;
static const RcApi *registered;
static RcFn plus_slot, triple_slot;
static RcFunction generated[2];
static const uint64_t native_base=UINT64_C(0x10000000);
static int guest_permit(void *ctx,uint64_t address,size_t bytes,int write) {
    const GuestRawWindow *window=(const GuestRawWindow *)ctx;
    return window && write==1 && bytes>0 && address>=window->begin &&
        address<=window->end && bytes<=window->end-address;
}
static int guest_pin(void *ctx) {
    GuestRawWindow *win=(GuestRawWindow *)ctx;
    if(!win)return 0;
    ++win->pins;
    return 1;
}
static void guest_unpin(void *ctx) {
    GuestRawWindow *win=(GuestRawWindow *)ctx;
    if(!win)abort();
    ++win->unpins;
}
static void guest_fatal(BbCpu *cpu,uint64_t target,uint64_t next,void *ctx){
    (void)cpu;(void)target;(void)next;(void)ctx;
    abort(); /* no PS4 guest fallback */
}
static int native_vm_read(uint64_t address,uint64_t *result) {
    ShytNativeVmLeaseV386 lease={0};
    if(!result || !shyt_native_vm_pin_v386(native_vm,&lease))return 0;
    int ok=shyt_native_vm_read_v386(&lease,address,8,result);
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    return ok;
}
static void pop_native(BbCpu *cpu) {
    uint64_t ret=0;
    if(!native_vm_read(cpu->r[4],&ret))abort();
    cpu->r[4]+=8;
    cpu->rip=ret;
}
static void generated_plus(BbCpu *cpu){cpu->r[0]+=7;pop_native(cpu);}
static void generated_triple(BbCpu *cpu){cpu->r[0]*=3;pop_native(cpu);}
static const RcFunction *synthetic_init(const RcApi *api,size_t *count) {
    if(!api||!count||api->version!=BB_RECOMP_API_VERSION)return NULL;
    registered=api;
    plus_slot=NULL;triple_slot=NULL;
    generated[0]=(RcFunction){0x5000,16,0x111,generated_plus,&plus_slot};
    generated[1]=(RcFunction){0x6000,32,0x222,generated_triple,&triple_slot};
    *count=2;
    return generated;
}
static int owner_mock_attest(void *ctx,uint64_t target,uint64_t size,uint64_t hash){
    unsigned *count=(unsigned *)ctx;
    ++*count;
    return (target==native_base+0x5000 && size==16 && hash==0x111) ||
           (target==native_base+0x6000 && size==32 && hash==0x222);
}
static int main_test(void) {
    static const char *names[23]={
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
    };
    const uint64_t guest_stack_base=UINT64_C(0x0000600000000000);
    const uint64_t outbase=UINT64_C(0x0000400000000000);
    const uint64_t readonlybase=UINT64_C(0x0000500000000000);
    const uint64_t writeonlybase=UINT64_C(0x0000700000000000);
    ShytNativeOsVmV388 owner={0};
    ShytNativeStackV383 logical={0},unready={0};
    ShytNativeBootChainV384 chain={0};
    ShytNativeVmV386 *vm=&owner.vm,unsealed={0};
    ShytUnifiedImportV387 unified={0};
    ShytAotServicesV245 services={0};
    ShytMathImportDesc desc[23];
    ShytMathImportTable math={0};
    ShytClockTargetsV239 clocks={native_base,0x3000,0x3020};
    RcApi strict={0};
    uint64_t raw_stack[16]={0};
    GuestRawWindow window={(uint64_t)(uintptr_t)&raw_stack[0],
                           (uint64_t)(uintptr_t)&raw_stack[16],0,0};
    BbCpu cpu={0},prior={0};
    ShytDirectStatsV259 stats={0};
    unsigned attests=0;
    uint64_t stored=0;
    CHECK(shyt_strict_aot_base_v381(&strict,native_base));
    CHECK(shyt_native_os_vm_init_v388(&owner));
    /* Four OS allocations: stack R/W, read-only, output R/W, W-only.
     * Their backing is allocated, protected and owned by V388. */
    CHECK(shyt_native_os_vm_add_v388(&owner,guest_stack_base,32,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&owner,readonlybase,8,
        SHYT_V386_READ));
    CHECK(shyt_native_os_vm_add_v388(&owner,outbase,16,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&owner,writeonlybase,8,
        SHYT_V386_WRITE));
    atomic_store(&owner.allocations[1].words[0],0xBAD);
    CHECK(shyt_native_stack_init_v383(
        &logical,owner.allocations[0].words,32,guest_stack_base));
    CHECK(shyt_native_os_vm_seal_v388(&owner));
    CHECK(shyt_native_os_vm_mapping_v388(&owner)==vm);
    CHECK(vm->region_count==4);
    native_vm=vm;
    {
        MEMORY_BASIC_INFORMATION info={0};
        CHECK(VirtualQuery(owner.allocations[1].words,
                           &info,sizeof(info))==sizeof(info));
        CHECK(info.Protect==PAGE_READONLY);
        CHECK(VirtualQuery(owner.allocations[0].words,
                           &info,sizeof(info))==sizeof(info));
        CHECK(info.Protect==PAGE_READWRITE);
    }
    for(size_t i=0;i<23;i++){desc[i].name=names[i];desc[i].offset=0x1000+i*16;}
    CHECK(shyt_math_import_table_v224_init(&math,native_base,desc,23));
    CHECK(!shyt_native_boot_preflight_v384(&services,&strict,&logical));
    CHECK(shyt_aot_services_bootstrap_v245(
        &services,&strict,&math,&clocks,
        guest_permit,&window,guest_fatal,&window,
        guest_pin,guest_unpin,&window,synthetic_init));
    CHECK(registered==services.published_api);
    CHECK(shyt_native_boot_preflight_v384(&services,&strict,&logical));
    CHECK(!shyt_native_boot_preflight_v384(&services,&strict,&unready));
    {
        ShytAotServicesV245 forged=services;
        forged.published_api=&forged.clock.api;
        forged.math.table.entries[0].offset=generated[0].offset;
        CHECK(!shyt_native_boot_preflight_v384(&forged,&strict,&logical));
        forged.math.table=services.math.table;
        forged.clock.targets.read_tsc_offset=generated[0].offset;
        CHECK(!shyt_native_boot_preflight_v384(&forged,&strict,&logical));
    }
    CHECK(!shyt_native_boot_finalize_multiregion_v387(
        &chain,&services,&strict,&logical,&unsealed,owner_mock_attest,&attests));
    CHECK(!shyt_native_boot_finalize_multiregion_v387(
        &chain,&services,&strict,&unready,vm,owner_mock_attest,&attests));
    CHECK(!attests && plus_slot==NULL && triple_slot==NULL);
    CHECK(shyt_native_boot_finalize_multiregion_v387(
        &chain,&services,&strict,&logical,vm,owner_mock_attest,&attests));
    CHECK(chain.route.stack_write==shyt_native_vm_stack_write_v386);
    CHECK(chain.route.stack_context==vm);
    CHECK(attests==2 && chain.published);
    CHECK(chain.proof.functions_attested==2);
    CHECK(chain.proof.owner_game_startup_proven==0);
    CHECK(chain.proof.no_guest_fallback_callbacks==1);
    CHECK(services.native_only_finalized_v384);
    CHECK(plus_slot==generated_plus && triple_slot==generated_triple);
    CHECK(services.published_api==registered);
    CHECK(registered->step==strict.step && registered->bail==strict.bail);
    CHECK(registered->tail!=strict.tail);
    CHECK(!shyt_native_boot_preflight_v384(&services,&strict,&logical));
    CHECK(!shyt_native_boot_finalize_multiregion_v387(
        &chain,&services,&strict,&logical,vm,owner_mock_attest,&attests));
    CHECK(!shyt_aot_services_link_direct_v261(
        &services,owner_mock_attest,&attests,&stats));
    CHECK(!shyt_aot_services_revoke_direct_v268(&services,&stats));
    CHECK(plus_slot==generated_plus && triple_slot==generated_triple);
    CHECK(!shyt_native_aot_dispose_v382(&chain.route));
    /* V387 final importer and V382 AOT dispatcher BOTH use V386, not
     * the V383 preflight-only sidecar or a host pointer alias. */
    {
        ShytMathImportDesc invalid[23];
        memcpy(invalid,desc,sizeof invalid);
        invalid[1].name=invalid[0].name;
        CHECK(!shyt_unified_import_prepare_v387(
            &unified,&services,&chain,vm,invalid,23));
        CHECK(!unified.ready && !unified.published);
    }
    CHECK(shyt_unified_import_prepare_v387(
        &unified,&services,&chain,vm,desc,23));
    CHECK(!shyt_unified_import_prepare_v387(
        &unified,&services,&chain,vm,desc,23));
    CHECK(shyt_unified_import_publish_v387(&unified));
    CHECK(!shyt_unified_import_publish_v387(&unified));
    CHECK(registered==services.published_api);
    CHECK(registered->call==services.clock.api.call);
    CHECK(registered->step==strict.step && registered->bail==strict.bail);
    cpu.r[0]=4;
    cpu.r[4]=guest_stack_base+24*8;
    prior=cpu;
    registered->call(&cpu,native_base+0x5000,0x12345678);
    CHECK(cpu.r[0]==11 && cpu.rip==0x12345678);
    CHECK(cpu.r[4]==prior.r[4]);
    CHECK(native_vm_read(guest_stack_base+23*8,&stored));
    CHECK(stored==0x12345678);
    CHECK(shyt_native_vm_stack_write_v386(
        vm,guest_stack_base+24*8,0xABCD));
    cpu.rip=native_base+0x6000;
    registered->tail(&cpu);
    CHECK(cpu.r[0]==33 && cpu.rip==0xABCD);
    CHECK(cpu.r[4]==guest_stack_base+25*8);
    /* V387 bypasses legacy raw host-pointer math/clock wrappers.
     * AOT, 23 math and 2 clock callbacks share V386 permissioned memory. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[4]=guest_stack_base+24*8;
    cpu.v[0].fd[0]=2.0;cpu.v[1].fd[0]=5.0;
    registered->call(&cpu,native_base+desc[18].offset,0x7001);
    CHECK(cpu.v[0].fd[0]==32.0 && cpu.rip==0x7001);
    CHECK(cpu.r[4]==guest_stack_base+24*8);
    CHECK(native_vm_read(guest_stack_base+23*8,&stored));
    CHECK(stored==0x7001);
    registered->call(&cpu,native_base+clocks.get_tsc_frequency_offset,0x7002);
    CHECK(cpu.r[0]==UINT64_C(1600000000) && cpu.rip==0x7002);
    registered->call(&cpu,native_base+clocks.read_tsc_offset,0x7003);
    CHECK(cpu.r[0]<UINT64_C(160000000000) && cpu.rip==0x7003);
    CHECK(window.pins==0 && window.unpins==0);

    /* Full 23-known-import positive surface, both float precisions. */
    for(size_t idx=0;idx<23;idx++) {
        memset(&cpu,0,sizeof(cpu));
        cpu.r[4]=guest_stack_base+24*8;
        cpu.r[RDI]=(idx==14 || idx==15)?outbase+3*8:2;
        if(names[idx][strlen(names[idx])-1]=='f') {
            cpu.v[0].f[0]=0.5f;cpu.v[1].f[0]=0.75f;
        } else {
            cpu.v[0].fd[0]=0.5;cpu.v[1].fd[0]=0.75;
        }
        const uint64_t next=UINT64_C(0xA000)+(uint64_t)idx;
        CHECK(shyt_unified_import_try_v387(
             &unified,&cpu,native_base+desc[idx].offset,next)==1);
        CHECK(cpu.rip==next && cpu.r[4]==guest_stack_base+24*8);
        CHECK(native_vm_read(guest_stack_base+23*8,&stored));
        CHECK(stored==next);
        if(idx==14 || idx==15) {
            ShytNativeVmLeaseV386 lease={0};
            uint64_t exponent_value=UINT64_MAX;
            CHECK(shyt_native_vm_pin_v386(vm,&lease));
            CHECK(shyt_native_vm_read_v386(
                &lease,outbase+3*8,4,&exponent_value));
            CHECK(exponent_value==0);
            CHECK(shyt_native_vm_unpin_v386(&lease));
        }
    }
    CHECK(window.pins==0 && window.unpins==0);

    /* Invalid frexp pointer must not touch CPU or guest memory. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[4]=guest_stack_base+24*8;
    cpu.r[RDI]=outbase+16*8;
    cpu.v[0].fd[0]=8.0;
    prior=cpu;
    CHECK(native_vm_read(guest_stack_base+23*8,&stored));
    const uint64_t previous_return=stored;
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+desc[14].offset,0xB001)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    CHECK(native_vm_read(guest_stack_base+23*8,&stored));
    CHECK(stored==previous_return);
    cpu.r[RDI]=guest_stack_base+23*8;
    prior=cpu;
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+desc[14].offset,0xB002)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    /* A R-only region may never receive frexp's four-byte exponent. */
    cpu.r[RDI]=readonlybase;
    prior=cpu;
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+desc[14].offset,0xB004)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    CHECK(atomic_load(&owner.allocations[1].words[0])==0xBAD);
    /* Four bytes cannot cross an atomic backing-word boundary. */
    cpu.r[RDI]=outbase+7;
    prior=cpu;
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+desc[14].offset,0xB005)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    /* A W-only region IS a valid output destination, but cannot be read
     * through VM READ. Prove mapped word was really written atomically. */
    cpu.r[RDI]=writeonlybase;
    cpu.v[0].fd[0]=8.0;
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+desc[14].offset,0xB006)==1);
    CHECK(atomic_load(&owner.allocations[3].words[0])==4);
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+0xFAFF,0xB003)==0);
    CHECK(window.pins==0 && window.unpins==0);
    /* Close denies future imports (known route -1), without mutating CPU. */
    /* The published native dispatcher requires OS pages for the
     * process lifetime; do not VirtualFree while RcApi is published. */
    CHECK(shyt_native_os_vm_close_v388(&owner));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[4]=guest_stack_base+24*8;
    prior=cpu;
    CHECK(shyt_unified_import_try_v387(
        &unified,&cpu,native_base+desc[18].offset,0xB007)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    CHECK(shyt_native_vm_quiescent_v386(vm));
    CHECK(!shyt_native_os_vm_release_v388(&owner,0));
    return 0; /* Windows OS reclaims mapped pages at process exit */
}
#endif
int main(void) {
#if defined(_WIN32)
    CHECK(!main_test());
    puts("NATIVE_V388_WIN64_OS_PAGE_BACKED_AOT_25_IMPORTS_PASS");
#else
    puts("NATIVE_V388_NON_WINDOWS_BUILD_ONLY_QPC_NOT_SUPPORTED");
#endif
    return 0;
}
