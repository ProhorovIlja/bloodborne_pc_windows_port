/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real V245 math/clock route + V381/V382/V383 synthetic native AOT,
 * built against pinned upstream RcApi/BbCpu C types on Windows AMD64.
 * Host pointers for math/clock and logical guest stack are deliberately
 * separate; DO NOT infer unified VM or original-game memory parity.
 */
#include "native_boot_chain_v384.h"
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
    /* Legacy math imports still use a separately verified host-alias
     * stack. This is not a unified synthetic VM. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[4]=(uint64_t)(uintptr_t)&raw_stack[8];
    cpu.v[0].fd[0]=2.0;cpu.v[1].fd[0]=5.0;
    registered->call(&cpu,native_base+desc[18].offset,0x7001);
    CHECK(cpu.v[0].fd[0]==32.0 && cpu.rip==0x7001);
    CHECK(cpu.r[4]==(uint64_t)(uintptr_t)&raw_stack[8]);
    registered->call(&cpu,native_base+clocks.get_tsc_frequency_offset,0x7002);
    CHECK(cpu.r[0]==UINT64_C(1600000000) && cpu.rip==0x7002);
    CHECK(window.pins==2 && window.unpins==2);
    return 0;
}
#endif
int main(void) {
#if defined(_WIN32)
    CHECK(!main_test());
    puts("NATIVE_V384_WIN64_V245_MATH_CLOCK_V382_V383_AOT_COMPOSITION_PASS");
#else
    puts("NATIVE_V384_NON_WINDOWS_BUILD_ONLY_QPC_NOT_SUPPORTED");
#endif
    return 0;
}
