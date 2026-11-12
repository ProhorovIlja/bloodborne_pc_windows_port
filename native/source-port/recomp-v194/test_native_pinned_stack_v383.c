/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host-owned synthetic atomic guest memory wired to V382 CALL/TAIL.
 * Never tests the original Bloodborne 1.09 executable or guest ABI parity.
 */
#include "full_cpu_abi_v194.h"
#include "native_aot_route_v382.h"
#include "native_pinned_stack_v383.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V383_ASSERT_LINE_%d\n",__LINE__);return 1;}}while(0)
static ShytNativeStackV383 *active_stack;
static void native_return(BbCpu *cpu) {
    uint64_t back=0;
    if (!shyt_native_stack_read_v383(active_stack,cpu->r[4],&back))
        abort();
    cpu->rip=back;
    cpu->r[4]+=8;
}
static void native_add(BbCpu *cpu){cpu->r[0]+=7;native_return(cpu);}
static void native_mul(BbCpu *cpu){cpu->r[0]*=3;native_return(cpu);}
static int synthetic_attest(void *ctx,uint64_t at,uint64_t size,uint64_t hash){
    unsigned *checks=(unsigned *)ctx;
    ++*checks;
    return (at==0x400100 && size==16 && hash==0x111) ||
           (at==0x400200 && size==32 && hash==0x222);
}
static int exercise(void){
    ShytNativeStackV383 stack={0},wrong={0};
    _Atomic(uint64_t) words[16];
    const uint64_t base=UINT64_C(0x0000600000000000);
    RcApi strict={0};
    RcFn slot_add=NULL,slot_mul=NULL;
    RcFunction functions[]={
        {0x100,16,0x111,native_add,&slot_add},
        {0x200,32,0x222,native_mul,&slot_mul}
    };
    ShytStrictAotProofV381 proof={0};
    ShytNativeAotRouteV382 route={0};
    BbCpu cpu={0},prior;
    unsigned checks=0;
    uint64_t value=0;
    for(size_t i=0;i<16;i++)atomic_init(&words[i],UINT64_C(0xC0FFEE));
    CHECK(!shyt_native_stack_init_v383(NULL,words,16,base));
    CHECK(!shyt_native_stack_init_v383(&wrong,NULL,16,base));
    CHECK(!shyt_native_stack_init_v383(&wrong,words,0,base));
    CHECK(!shyt_native_stack_init_v383(&wrong,words,16,0));
    CHECK(!shyt_native_stack_init_v383(&wrong,words,16,base+1));
    CHECK(!shyt_native_stack_init_v383(&wrong,words,16,UINT64_MAX-7));
    CHECK(!shyt_native_stack_pin_v383(&wrong));
    CHECK(!shyt_native_stack_close_v383(&wrong));
    CHECK(!shyt_native_stack_quiescent_v383(&wrong));
    CHECK(shyt_native_stack_init_v383(&stack,words,16,base));
    CHECK(!shyt_native_stack_init_v383(&stack,words,16,base));
    CHECK(!shyt_native_stack_write_v383(NULL,base,2));
    CHECK(!shyt_native_stack_write_v383(&stack,base-8,2));
    CHECK(!shyt_native_stack_write_v383(&stack,base+1,2));
    CHECK(!shyt_native_stack_write_v383(&stack,base+16*8,2));
    CHECK(!shyt_native_stack_write_v383(&stack,UINT64_MAX,2));
    CHECK(atomic_load(&words[0])==UINT64_C(0xC0FFEE));
    CHECK(shyt_native_stack_write_v383(&stack,base+13*8,0xAABBCCDD));
    CHECK(shyt_native_stack_read_v383(&stack,base+13*8,&value));
    CHECK(value==0xAABBCCDD);
    value=0xBAD;
    CHECK(!shyt_native_stack_read_v383(&stack,base-8,&value));
    CHECK(value==0xBAD);
    CHECK(!shyt_native_stack_read_v383(&stack,base,NULL));
    CHECK(!shyt_native_stack_unpin_v383(&stack)); /* underflow blocked */
    CHECK(shyt_strict_aot_base_v381(&strict,0x400000));
    CHECK(shyt_strict_aot_activate_v381(&strict,functions,2,
        0x400000,synthetic_attest,&checks,&proof));
    CHECK(checks==2 && proof.functions_attested==2);
    CHECK(shyt_native_aot_prepare_v382(&route,&strict,functions,2,
        &proof,shyt_native_stack_write_v383,&stack));
    active_stack=&stack;
    CHECK(shyt_native_aot_lookup_v382(&route,0x400100)==native_add);
    cpu.r[0]=10;
    cpu.r[4]=base+14*8;
    prior=cpu;
    CHECK(!shyt_native_aot_try_call_v382(&route,&cpu,0x400999,0xDADA));
    CHECK(!memcmp(&prior,&cpu,sizeof(cpu)));
    CHECK(shyt_native_aot_try_call_v382(&route,&cpu,0x400100,0xDADA));
    CHECK(cpu.r[0]==17 && cpu.rip==0xDADA);
    CHECK(cpu.r[4]==base+14*8);
    CHECK(shyt_native_stack_read_v383(&stack,base+13*8,&value));
    CHECK(value==0xDADA);
    /* TAIL invokes original native function without writing another RSP. */
    CHECK(shyt_native_stack_write_v383(&stack,base+14*8,0xBBBB));
    cpu.r[4]=base+14*8;
    cpu.rip=0x400200;
    CHECK(shyt_native_aot_try_tail_v382(&route,&cpu));
    CHECK(cpu.r[0]==51 && cpu.rip==0xBBBB);
    CHECK(cpu.r[4]==base+15*8);
    /* Stack bounds or closing must deny native CALL before changing CPU. */
    cpu.r[4]=base;
    prior=cpu;
    CHECK(!shyt_native_aot_try_call_v382(&route,&cpu,0x400100,0xCCCC));
    CHECK(!memcmp(&prior,&cpu,sizeof(cpu)));
    CHECK(shyt_native_stack_pin_v383(&stack));
    CHECK(shyt_native_stack_pin_v383(&stack));
    CHECK(shyt_native_stack_close_v383(&stack));
    CHECK(!shyt_native_stack_quiescent_v383(&stack));
    CHECK(!shyt_native_stack_pin_v383(&stack));
    value=0xCAFE;
    CHECK(!shyt_native_stack_read_v383(&stack,base+14*8,&value));
    CHECK(value==0xCAFE);
    CHECK(!shyt_native_stack_write_v383(&stack,base+14*8,0xDEAD));
    CHECK(atomic_load(&words[14])==0xBBBB);
    cpu.r[4]=base+14*8;
    prior=cpu;
    CHECK(!shyt_native_aot_try_call_v382(&route,&cpu,0x400100,0xCCCC));
    CHECK(!memcmp(&prior,&cpu,sizeof(cpu)));
    CHECK(shyt_native_stack_unpin_v383(&stack));
    CHECK(!shyt_native_stack_quiescent_v383(&stack));
    CHECK(shyt_native_stack_unpin_v383(&stack));
    CHECK(shyt_native_stack_quiescent_v383(&stack));
    CHECK(!shyt_native_stack_unpin_v383(&stack));
    CHECK(shyt_native_stack_close_v383(&stack));
    CHECK(!shyt_native_stack_init_v383(&stack,words,16,base));
    /* Unpublished routes can be freed only after all native call users exit. */
    CHECK(shyt_native_aot_dispose_v382(&route));
    return 0;
}
int main(void){
    CHECK(!exercise());
    puts("NATIVE_V383_PINNED_ATOMIC_GUEST_STACK_AOT_CALL_TAIL_PASS");
    return 0;
}
