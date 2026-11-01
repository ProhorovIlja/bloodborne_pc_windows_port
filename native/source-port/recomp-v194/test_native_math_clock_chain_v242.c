/* SPDX-License-Identifier: GPL-2.0-or-later
 * V242: real pinned public RcApi V4 route composition. NO retail EBOOT.
 * Original callback -> validated math V226 -> validated Win32 clocks V239.
 */
#include "native_math_rcapi_route_v226.h"
#include "native_clock_rcapi_route_v239.h"
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint64_t first, last;
    int deny;
} Region;
static int pinned, enters, leaves, fallbacks, faults;
static jmp_buf trap;
static int permit(void *ctx,uint64_t address,size_t size,int write) {
    const Region *r=(const Region *)ctx;
    return !r->deny && write && address >= r->first &&
        address <= r->last && size <= r->last-address;
}
static int enter(void *ctx) {
    (void)ctx;
    if (pinned) return 0;
    pinned=1;++enters;return 1;
}
static void leave(void *ctx) {
    (void)ctx;
    assert(pinned);pinned=0;++leaves;
}
static void fatal_guest(BbCpu *cpu,uint64_t target,uint64_t next,void *ctx) {
    (void)cpu;(void)target;(void)next;(void)ctx;
    assert(!pinned);
    ++faults;
    longjmp(trap,1);
}
static void previous_call(BbCpu *cpu,uint64_t target,uint64_t next) {
    (void)target;(void)next;
    assert(!pinned && cpu);
    ++fallbacks;
}
static uint64_t previous_step(BbCpu *cpu){return cpu->rip;}
static void previous_tail(BbCpu *cpu){(void)cpu;}
static void previous_bail(BbCpu *cpu,uint64_t rsp){(void)cpu;(void)rsp;}

int main(void) {
#if defined(_WIN32)
    static const char *names[23] = {
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
    };
    ShytMathImportDesc entries[23];
    for (size_t i=0;i<23;i++) {
        entries[i].name=names[i];entries[i].offset=UINT64_C(0x100)+i*16;
    }
    const uint64_t base=UINT64_C(0x10000000);
    ShytMathImportTable math_table;
    assert(shyt_math_import_table_v224_init(&math_table,base,entries,23));
    RcApi original={0};
    original.version=BB_RECOMP_API_VERSION;
    original.image_base=base;
    original.call=previous_call;original.step=previous_step;
    original.tail=previous_tail;original.bail=previous_bail;
    uint64_t stack[16]={0};
    Region region={(uint64_t)(uintptr_t)&stack[0],
                   (uint64_t)(uintptr_t)&stack[16],0};
    ShytMathRcApiRoute math;
    assert(shyt_math_rcapi_route_v226_install_pinned(
        &math,&original,&math_table,permit,&region,
        fatal_guest,0,enter,leave,0));
    const RcApi *math_api=shyt_math_rcapi_route_v226_api(&math);
    assert(math_api && math_api->call!=original.call);

    ShytClockRouteV239 clock;
    ShytClockTargetsV239 clock_targets={base,0x2010,0x2030};
    assert(shyt_clock_rcapi_install_v239(&clock,math_api,&clock_targets,
        permit,&region,fatal_guest,0,enter,leave,0));
    const RcApi *final_api=shyt_clock_rcapi_api_v239(&clock);
    assert(final_api && final_api->call!=math_api->call);
    assert(final_api->step==original.step && final_api->tail==original.tail);

    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RSP]=(uint64_t)(uintptr_t)&stack[8];
    const uint64_t sp=cpu.r[RSP];
    cpu.v[0].fd[0]=2.0;cpu.v[1].fd[0]=3.0;
    // Actual V222 host math function through V223 guest FP ABI and V226,
    // entered by the FINAL V239 RcApi.call rather than directly.
    final_api->call(&cpu,base+entries[18].offset,0x555);
    assert(cpu.v[0].fd[0]==8.0 && cpu.rip==0x555 && cpu.r[RSP]==sp);
    assert(fallbacks==0);
    final_api->call(&cpu,base+clock_targets.get_tsc_frequency_offset,0x556);
    assert(cpu.r[RAX]==UINT64_C(1600000000));
    assert(cpu.rip==0x556 && cpu.r[RSP]==sp);
    uint64_t ticks=0;
    final_api->call(&cpu,base+clock_targets.read_tsc_offset,0x557);
    ticks=cpu.r[RAX];
    assert(cpu.rip==0x557 && ticks<UINT64_C(160000000000));
    // Unrecognized imported function must reach ORIGINAL once and unchanged.
    const uint64_t rax=cpu.r[RAX];
    final_api->call(&cpu,base+0xdead,0x558);
    assert(fallbacks==1 && cpu.r[RAX]==rax && cpu.rip==0x557);
    // Known clock import with bad stack must fault AFTER releasing the pin;
    // it must NEVER fall through to an unvalidated original import.
    region.deny=1;
    if (setjmp(trap)==0)
        final_api->call(&cpu,base+clock_targets.read_tsc_offset,0x559);
    assert(faults==1 && fallbacks==1 && !pinned);
    // Known math import goes through math validator, not unknown fallback.
    if (setjmp(trap)==0)
        final_api->call(&cpu,base+entries[18].offset,0x560);
    assert(faults==2 && fallbacks==1 && !pinned);
    assert(enters==leaves);
#endif
    puts("SHYT_V242_PINNED_NATIVE_MATH_CLOCK_RCAPI_CHAIN_PASS");
    return 0;
}
