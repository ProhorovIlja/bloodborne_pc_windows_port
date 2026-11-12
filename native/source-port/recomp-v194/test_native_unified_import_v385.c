/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real V245 math/clock route + V381/V382/V383 synthetic native AOT,
 * built against pinned upstream RcApi/BbCpu C types on Windows AMD64.
 * Host pointers for math/clock and logical guest stack are deliberately
 * separate; DO NOT infer unified VM or original-game memory parity.
 */
#include "native_unified_import_v385.h"
/* The real pinned upstream V245 public header already defines BbCpu.
 * V194's standalone mirror cannot be included in that same C TU. */
#include <stddef.h>
_Static_assert(sizeof(BbCpu)==840 && offsetof(BbCpu,rip)==128,
               "pinned upstream BbCpu layout changed");
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V384_CHECK_LINE_%d\n",__LINE__);return 1;}}while(0)
#if defined(_WIN32)
typedef struct {
    uint64_t begin,end;
    unsigned pins,unpins;
} GuestRawWindow;
static ShytNativeStackV383 *native_stack;
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
static void pop_native(BbCpu *cpu) {
    uint64_t ret=0;
    if(!shyt_native_stack_read_v383(native_stack,cpu->r[4],&ret))abort();
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
    _Atomic(uint64_t) words[32];
    ShytNativeStackV383 logical={0},unready={0};
    ShytNativeBootChainV384 chain={0};
    ShytGuestVmV385 vm={0};
    ShytUnifiedImportV385 unified={0};
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
    for(size_t i=0;i<32;i++)atomic_init(&words[i],0);
    CHECK(shyt_strict_aot_base_v381(&strict,native_base));
    CHECK(shyt_native_stack_init_v383(&logical,words,32,guest_stack_base));
    native_stack=&logical;
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
    CHECK(!shyt_native_boot_finalize_v384(
        &chain,&services,&strict,&unready,owner_mock_attest,&attests));
    CHECK(!attests && plus_slot==NULL && triple_slot==NULL);
    CHECK(shyt_native_boot_finalize_v384(
        &chain,&services,&strict,&logical,owner_mock_attest,&attests));
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
    CHECK(!shyt_native_boot_finalize_v384(
        &chain,&services,&strict,&logical,owner_mock_attest,&attests));
    CHECK(!shyt_aot_services_link_direct_v261(
        &services,owner_mock_attest,&attests,&stats));
    CHECK(!shyt_aot_services_revoke_direct_v268(&services,&stats));
    CHECK(plus_slot==generated_plus && triple_slot==generated_triple);
    CHECK(!shyt_native_aot_dispose_v382(&chain.route));
    /* Final V385 route shares V384's exact logical guest stack mapping. */
    CHECK(shyt_guest_vm_init_v385(&vm,&logical));
    {
        ShytMathImportDesc invalid[23];
        memcpy(invalid,desc,sizeof invalid);
        invalid[1].name=invalid[0].name;
        CHECK(!shyt_unified_import_prepare_v385(
            &unified,&services,&chain,&vm,invalid,23));
        CHECK(!unified.ready && !unified.published);
    }
    CHECK(shyt_unified_import_prepare_v385(
        &unified,&services,&chain,&vm,desc,23));
    CHECK(!shyt_unified_import_prepare_v385(
        &unified,&services,&chain,&vm,desc,23));
    CHECK(shyt_unified_import_publish_v385(&unified));
    CHECK(!shyt_unified_import_publish_v385(&unified));
    CHECK(registered==services.published_api);
    CHECK(registered->call==services.clock.api.call);
    CHECK(registered->step==strict.step && registered->bail==strict.bail);
    cpu.r[0]=4;
    cpu.r[4]=guest_stack_base+24*8;
    prior=cpu;
    registered->call(&cpu,native_base+0x5000,0x12345678);
    CHECK(cpu.r[0]==11 && cpu.rip==0x12345678);
    CHECK(cpu.r[4]==prior.r[4]);
    CHECK(shyt_native_stack_read_v383(&logical,guest_stack_base+23*8,&stored));
    CHECK(stored==0x12345678);
    CHECK(shyt_native_stack_write_v383(
        &logical,guest_stack_base+24*8,0xABCD));
    cpu.rip=native_base+0x6000;
    registered->tail(&cpu);
    CHECK(cpu.r[0]==33 && cpu.rip==0xABCD);
    CHECK(cpu.r[4]==guest_stack_base+25*8);
    /* V385 bypasses legacy raw-pointer math/clock callbacks.
     * Math, clocks and native AOT all use identical logical stack region. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[4]=guest_stack_base+24*8;
    cpu.v[0].fd[0]=2.0;cpu.v[1].fd[0]=5.0;
    registered->call(&cpu,native_base+desc[18].offset,0x7001);
    CHECK(cpu.v[0].fd[0]==32.0 && cpu.rip==0x7001);
    CHECK(cpu.r[4]==guest_stack_base+24*8);
    CHECK(shyt_native_stack_read_v383(&logical,guest_stack_base+23*8,&stored));
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
        cpu.r[RDI]=(idx==14 || idx==15)?guest_stack_base+3*8:2;
        if(names[idx][strlen(names[idx])-1]=='f') {
            cpu.v[0].f[0]=0.5f;cpu.v[1].f[0]=0.75f;
        } else {
            cpu.v[0].fd[0]=0.5;cpu.v[1].fd[0]=0.75;
        }
        const uint64_t next=UINT64_C(0xA000)+(uint64_t)idx;
        CHECK(shyt_unified_import_try_v385(
             &unified,&cpu,native_base+desc[idx].offset,next)==1);
        CHECK(cpu.rip==next && cpu.r[4]==guest_stack_base+24*8);
        CHECK(shyt_native_stack_read_v383(&logical,guest_stack_base+23*8,&stored));
        CHECK(stored==next);
    }
    CHECK(window.pins==0 && window.unpins==0);

    /* Invalid frexp pointer must not touch CPU or guest memory. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[4]=guest_stack_base+24*8;
    cpu.r[RDI]=guest_stack_base+32*8;
    cpu.v[0].fd[0]=8.0;
    prior=cpu;
    CHECK(shyt_native_stack_read_v383(&logical,guest_stack_base+23*8,&stored));
    const uint64_t previous_return=stored;
    CHECK(shyt_unified_import_try_v385(
        &unified,&cpu,native_base+desc[14].offset,0xB001)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    CHECK(shyt_native_stack_read_v383(&logical,guest_stack_base+23*8,&stored));
    CHECK(stored==previous_return);
    cpu.r[RDI]=guest_stack_base+23*8;
    prior=cpu;
    CHECK(shyt_unified_import_try_v385(
        &unified,&cpu,native_base+desc[14].offset,0xB002)==-1);
    CHECK(memcmp(&prior,&cpu,sizeof(cpu))==0);
    CHECK(shyt_unified_import_try_v385(
        &unified,&cpu,native_base+0xFAFF,0xB003)==0);
    CHECK(window.pins==0 && window.unpins==0);
    return 0;
}
#endif
int main(void) {
#if defined(_WIN32)
    CHECK(!main_test());
    puts("NATIVE_V385_WIN64_UNIFIED_LOGICAL_VM_MATH_CLOCK_AOT_PASS");
#else
    puts("NATIVE_V385_NON_WINDOWS_BUILD_ONLY_QPC_NOT_SUPPORTED");
#endif
    return 0;
}
