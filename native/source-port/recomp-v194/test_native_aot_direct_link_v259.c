/* SPDX-License-Identifier: GPL-2.0-or-later
 * V259 genuine RcFunction/RcFn direct link slots, synthetic source hashes.
 * A valid owner build-time code attestation is required by the API.
 */
#include "native_aot_direct_link_v259.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void generated_a(BbCpu *cpu) { cpu->r[RAX]+=1; }
static void generated_b(BbCpu *cpu) { cpu->r[RAX]*=2; }
typedef struct {
    uint64_t image_base;
    int permit_b;
    unsigned checks;
} Attest;
static int exact_hash(void *context,uint64_t target,uint64_t bytes,uint64_t hash) {
    Attest *ctx=(Attest*)context;
    ++ctx->checks;
    if(target==ctx->image_base+0x100)
        return bytes==16 && hash==UINT64_C(0x1111);
    if(target==ctx->image_base+0x200)
        return ctx->permit_b && bytes==16 && hash==UINT64_C(0x2222);
    return 0;
}
int main(void) {
    const uint64_t base=UINT64_C(0x10000000);
    RcFn direct_a=generated_b; // stale pointer must be replaced
    RcFn direct_b=generated_a; // stale pointer must be CLEARED
    RcFunction functions[3]={
       {0x100,16,UINT64_C(0x1111),generated_a,&direct_a},
       {0x200,16,UINT64_C(0x2222),generated_b,&direct_b},
       {0x300,16,UINT64_C(0x3333),generated_a,NULL}
    };
    ShytDirectStatsV259 stats={0};
    Attest ctx={base,0,0};
    assert(!shyt_aot_activate_direct_slots_v259(
        functions,3,base,NULL,&ctx,&stats));
    assert(direct_a==generated_b && direct_b==generated_a);
    assert(shyt_aot_activate_direct_slots_v259(
        functions,3,base,exact_hash,&ctx,&stats));
    assert(stats.direct==1 && stats.kept_indirect==1 && stats.no_slot==1);
    assert(ctx.checks==2 && direct_a==generated_a && direct_b==NULL);
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=40;
    assert(direct_a);
    direct_a(&cpu);
    assert(cpu.r[RAX]==41);
    // Once the verified manifest permits the other function, native
    // generated code may call it directly with the original BbCpu ABI.
    ctx.permit_b=1;
    assert(shyt_aot_activate_direct_slots_v259(
        functions,3,base,exact_hash,&ctx,&stats));
    assert(stats.direct==2 && !stats.kept_indirect);
    assert(direct_b==generated_b);
    direct_b(&cpu);
    assert(cpu.r[RAX]==82);
    // Revoking one function's hash/patch authorization CLEARS its slot.
    ctx.permit_b=0;
    assert(shyt_aot_activate_direct_slots_v259(
        functions,3,base,exact_hash,&ctx,&stats));
    assert(direct_b==NULL && direct_a==generated_a);
    // Malformed offsets never reach the attestation callback and must
    // not disturb the last known live direct dispatch table.
    unsigned before=ctx.checks;
    functions[1].offset=functions[0].offset;
    assert(!shyt_aot_activate_direct_slots_v259(
        functions,3,base,exact_hash,&ctx,&stats));
    assert(ctx.checks==before && direct_a==generated_a);
    // V269: two AOT entries must NEVER share one generated direct slot.
    // Otherwise the final entry could silently change the other's call.
    functions[1].offset=0x200;
    functions[1].direct=functions[0].direct;
    assert(!shyt_aot_activate_direct_slots_v259(
        functions,3,base,exact_hash,&ctx,&stats));
    assert(!shyt_aot_revoke_direct_slots_v268(functions,3,base,&stats));
    assert(ctx.checks==before && direct_a==generated_a);
    functions[1].direct=&direct_b;
    assert(shyt_aot_direct_slots_unique_v269(functions,3));

    puts("SHYT_V259_REAL_AOT_DIRECT_FUNCTION_LINK_ATTESTATION_PASS");
}
