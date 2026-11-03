/* SPDX-License-Identifier: GPL-2.0-or-later
 * V252 regression: NEVER pin/abort on original non-math RcApi.call targets.
 * Synthetic addresses/CPU only; genuine public pinned AOT interface.
 */
#include "native_math_rcapi_route_v226.h"
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int pins, unpins, original_calls, pin_allowed=1, faults;
static jmp_buf fault_boundary;
static const uint64_t base=UINT64_C(0x10000000);
static int allow_memory(void *ctx,uint64_t at,size_t len,int write) {
    uint64_t *stack=(uint64_t *)ctx;
    uint64_t first=(uint64_t)(uintptr_t)stack;
    return write && at>=first && len<=128 && at-first<=128-len;
}
static int enter_pin(void *ctx) {
    (void)ctx;++pins;return pin_allowed;
}
static void leave_pin(void *ctx) {
    (void)ctx;++unpins;
}
static void fatal_guest(BbCpu *cpu,uint64_t target,uint64_t next,void *ctx) {
    (void)cpu;(void)target;(void)next;(void)ctx;
    ++faults;
    longjmp(fault_boundary,1);
}
static uint64_t original_step(BbCpu *cpu) {return cpu->rip;}
static void original_call(BbCpu *cpu,uint64_t target,uint64_t next) {
    ++original_calls;
    assert(cpu && target==base+UINT64_C(0x9000));
    cpu->rip=next;
}
static void original_tail(BbCpu *cpu) {(void)cpu;}
static void original_bail(BbCpu *cpu,uint64_t sp) {(void)cpu;(void)sp;}
int main(void) {
#if defined(_WIN32)
    const char *names[23]={
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
    };
    ShytMathImportDesc input[23];
    for(size_t i=0;i<23;++i) {
        input[i].offset=0x100+16*i;
        input[i].name=names[i];
    }
    ShytMathImportTable table;
    assert(shyt_math_import_table_v224_init(&table,base,input,23));
    RcApi original={0};
    original.version=BB_RECOMP_API_VERSION;
    original.image_base=base;
    original.step=original_step;
    original.call=original_call;
    original.tail=original_tail;
    original.bail=original_bail;
    uint64_t guest_stack[16]={0};
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RSP]=(uint64_t)(uintptr_t)&guest_stack[8];
    ShytMathRcApiRoute route={0};
    assert(shyt_math_rcapi_route_v226_install_pinned(
       &route,&original,&table,allow_memory,guest_stack,
       fatal_guest,0,enter_pin,leave_pin,0));
    const RcApi *published=shyt_math_rcapi_route_v226_api(&route);
    assert(published);
    // Pin is deliberately inaccessible. Unknown imports MUST remain
    // available: the old V226 killed the game instead of forwarding.
    pin_allowed=0;
    for(int i=0;i<200;++i) {
        published->call(&cpu,base+0x9000,0x4000u+(uint64_t)i);
        assert(cpu.rip==0x4000u+(uint64_t)i);
    }
    assert(original_calls==200 && pins==0 && unpins==0 && faults==0);
    // Known pow must fail CLOSED when the memory lease is unavailable.
    cpu.v[0].fd[0]=2.0;
    cpu.v[1].fd[0]=3.0;
    if(setjmp(fault_boundary)==0)
       published->call(&cpu,base+input[18].offset,0x4010);
    assert(faults==1 && pins==1 && unpins==0 && original_calls==200);
    // Once allowed, known math must complete and release allocation pin.
    pin_allowed=1;
    published->call(&cpu,base+input[18].offset,0x4011);
    assert(cpu.v[0].fd[0]==8.0 && cpu.rip==0x4011);
    assert(pins==2 && unpins==1 && original_calls==200);
#endif
    puts("SHYT_V252_MATH_UNKNOWN_TARGET_ZERO_PINS_AND_FAULT_ISOLATION_PASS");
    return 0;
}
