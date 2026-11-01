/* SPDX-License-Identifier: GPL-2.0-or-later
 * V245: end-to-end native boot registry: pinned RcApi -> 23 math -> TSC
 * -> bb_recomp_init -> registered compiled AOT C function.
 * Synthetic code only; no retail game bytes or runtime PS4 ELF.
 */
#include "native_aot_services_bootstrap_v245.h"
#include "native_aot_table_audit_v257.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const RcApi *g_registered_api;
static uint64_t g_math_target, g_clock_target, g_freq_target;
static int g_fallbacks, g_pins, g_leaves;
typedef struct { uint64_t begin, end; } Bounds;
static int permit(void *ctx, uint64_t at, size_t size, int write) {
    Bounds *b=(Bounds *)ctx;
    return write && size && at>=b->begin && at<=b->end &&
        size<=b->end-at;
}
static int pin(void *ctx) { (void)ctx; ++g_pins;return 1; }
static void unpin(void *ctx) { (void)ctx; ++g_leaves; }
static void fatal_memory(BbCpu *cpu, uint64_t target, uint64_t next, void *ctx) {
    (void)cpu;(void)target;(void)next;(void)ctx;
    /* This fixture never invokes a guest fault. */
    assert(0 && "unexpected guest memory error");
}
static void fallback(BbCpu *cpu,uint64_t target,uint64_t next) {
    (void)cpu;(void)target;(void)next;++g_fallbacks;
}
static uint64_t step(BbCpu *cpu) { return cpu->rip; }
static void tail(BbCpu *cpu) { (void)cpu; }
static void bail(BbCpu *cpu,uint64_t rsp) { (void)cpu;(void)rsp; }

static void generated_entry(BbCpu *cpu) {
    /* Emulates one AOT C function using published RcApi CALLS.
     * The final game's generated bb_recomp_init uses the same interface. */
    cpu->v[0].fd[0]=2.0;
    cpu->v[1].fd[0]=5.0;
    g_registered_api->call(cpu,g_math_target,0x501);
    assert(cpu->v[0].fd[0]==32.0 && cpu->rip==0x501);
    g_registered_api->call(cpu,g_freq_target,0x502);
    assert(cpu->r[RAX]==UINT64_C(1600000000) && cpu->rip==0x502);
    g_registered_api->call(cpu,g_clock_target,0x503);
    assert(cpu->r[RAX]<UINT64_C(160000000000) && cpu->rip==0x503);
}
static RcFunction generated[1];
static RcFn native_direct_slot=NULL;
static int direct_granted=0;
static int exact_guest_function_attestation(void *ctx,uint64_t target,
                                             uint64_t bytes,uint64_t hash) {
    const uint64_t base=*(const uint64_t *)ctx;
    return direct_granted && target==base+0x4000 &&
           bytes==16 && hash==UINT64_C(0xbeef);
}
static const RcFunction *synthetic_recomp_init(const RcApi *api,size_t *count) {
    if (!api || api->version!=BB_RECOMP_API_VERSION || !count) return NULL;
    g_registered_api=api;
    generated[0].offset=0x4000;
    generated[0].size=16;
    generated[0].hash=0xbeef;
    generated[0].fn=generated_entry;
    generated[0].direct=&native_direct_slot;
    *count=1;
    return generated;
}
int main(void) {
#if defined(_WIN32)
    const uint64_t base=UINT64_C(0x10000000);
    static const char *names[23]={
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
    };
    ShytMathImportDesc descs[23];
    for(size_t i=0;i<23;i++) {
        descs[i].offset=0x100+16*i;
        descs[i].name=names[i];
    }
    ShytMathImportTable math;
    assert(shyt_math_import_table_v224_init(&math,base,descs,23));
    RcApi api={0};
    api.version=BB_RECOMP_API_VERSION;api.image_base=base;
    api.step=step;api.call=fallback;api.tail=tail;api.bail=bail;
    ShytClockTargetsV239 clock={base,0x3000,0x3020};
    g_math_target=base+descs[18].offset;
    g_clock_target=base+clock.read_tsc_offset;
    g_freq_target=base+clock.get_tsc_frequency_offset;
    uint64_t stack[16]={0};
    Bounds bounds={(uint64_t)(uintptr_t)&stack[0],
                   (uint64_t)(uintptr_t)&stack[16]};
    /* V257: validate the registry before irreversible RcApi bootstrap.
     * These are entirely synthetic addresses/targets, no original game. */
    RcFunction audit[2]={{0x100,16,1,generated_entry,NULL},
                         {0x200,16,2,generated_entry,NULL}};
    assert(shyt_aot_table_valid_v257(audit,2,base));
    assert(!shyt_aot_table_valid_v257(NULL,2,base));
    assert(!shyt_aot_table_valid_v257(audit,0,base));
    assert(!shyt_aot_table_valid_v257(audit,1000001u,base));
    assert(!shyt_aot_table_valid_v257(audit,2,0));
    audit[0].fn=NULL;
    assert(!shyt_aot_table_valid_v257(audit,2,base));
    audit[0].fn=generated_entry;
    audit[0].size=0;
    assert(!shyt_aot_table_valid_v257(audit,2,base));
    audit[0].size=16;
    audit[1].offset=audit[0].offset;
    assert(!shyt_aot_table_valid_v257(audit,2,base));
    audit[1].offset=0x200;
    audit[0].offset=UINT64_MAX;
    assert(!shyt_aot_table_valid_v257(audit,2,base));
    audit[0].offset=0x100;
    audit[1].size=UINT64_MAX;
    assert(!shyt_aot_table_valid_v257(audit,2,base));
    audit[1].size=16;
    assert(shyt_aot_table_valid_v257(audit,2,base));
    ShytAotServicesV245 services={0};
    /* Invalid overlap is rejected WITHOUT installing either route. */
    ShytClockTargetsV239 bad={base,descs[18].offset,0x3020};
    assert(!shyt_aot_services_bootstrap_v245(
        &services,&api,&math,&bad,permit,&bounds,
        fatal_memory,0,pin,unpin,0,synthetic_recomp_init));
    assert(!services.published_api && !g_registered_api);
    assert(shyt_aot_services_bootstrap_v245(
        &services,&api,&math,&clock,permit,&bounds,
        fatal_memory,0,pin,unpin,0,synthetic_recomp_init));
    assert(services.functions && services.function_count==1);
    assert(services.functions[0].offset==0x4000 &&
           services.functions[0].fn==generated_entry);
    assert(g_registered_api==services.published_api);
    assert(g_registered_api->call!=api.call);
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RSP]=(uint64_t)(uintptr_t)&stack[8];
    const uint64_t original_rsp=cpu.r[RSP];
    services.functions[0].fn(&cpu);
    assert(cpu.r[RSP]==original_rsp);
    assert(g_fallbacks==0 && g_pins==3 && g_leaves==3);

    /* V261: native AOT direct-call slot is absent until owner-attested.
     * The no-game fixture deliberately denies, then grants, then revokes. */
    ShytDirectStatsV259 stats={0};
    assert(native_direct_slot==NULL);
    assert(!shyt_aot_services_link_direct_v261(
        &services,NULL,&base,&stats));
    assert(shyt_aot_services_link_direct_v261(
        &services,exact_guest_function_attestation,(void *)&base,&stats));
    assert(stats.direct==0 && stats.kept_indirect==1 &&
           native_direct_slot==NULL);
    direct_granted=1;
    assert(shyt_aot_services_link_direct_v261(
        &services,exact_guest_function_attestation,(void *)&base,&stats));
    assert(stats.direct==1 && native_direct_slot==generated_entry);
    cpu.r[RSP]=original_rsp;
    native_direct_slot(&cpu); /* actual AOT-style C -> C direct call */
    assert(g_fallbacks==0 && g_pins==6 && g_leaves==6);
    direct_granted=0;
    assert(shyt_aot_services_link_direct_v261(
        &services,exact_guest_function_attestation,(void *)&base,&stats));
    assert(stats.kept_indirect==1 && native_direct_slot==NULL);
#endif
    puts("SHYT_V245_REAL_RCAPI_NATIVE_AOT_BOOTSTRAP_SYNTHETIC_PASS");
    return 0;
}
