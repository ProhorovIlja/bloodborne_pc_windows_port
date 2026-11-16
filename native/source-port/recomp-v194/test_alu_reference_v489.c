/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "alu_v488.h"
#include <stdio.h>
#if defined(__x86_64__) && (defined(__clang__) || defined(__GNUC__))
#define OP(ins,reg) __asm__ volatile(ins " %[" #reg "],%[a]\n\tpushfq\n\tpopq %[f]" \
    : [a] "+&r"(a), [f] "=&r"(f) : [q] "r"(b), [l] "r"((uint32_t)b) : "cc","memory")
/* Never compile this test with red-zone storage: pushfq temporarily uses
 * one word below RSP. For Windows x64 the ABI has no red zone. */
#define OP32(ins) __asm__ volatile(ins " %[l],%k[a]\n\tpushfq\n\tpopq %[f]" \
    : [a] "+&r"(a), [f] "=&r"(f) : [l] "r"((uint32_t)b) : "cc","memory")
#define BOTH(ins) do {if(w==64){OP(ins "q",q);}else{OP32(ins "l");}}while(0)
static uint64_t hardware(enum bb_alu_v488 op,unsigned w,uint64_t a,uint64_t b,uint64_t *flags) {
    uint64_t f;
    switch(op) {
    case BB_ADD: BOTH("add"); break;
    case BB_SUB: BOTH("sub"); break;
    case BB_OR: BOTH("or"); break;
    case BB_AND: BOTH("and"); break;
    case BB_XOR: BOTH("xor"); break;
    case BB_CMP: BOTH("cmp"); break;
    default: BOTH("test"); break;
    }
    *flags=f;
    return a;
}
static int verify(unsigned w,uint64_t a,uint64_t b) {
    for(unsigned i=0;i<=BB_TEST;++i) {
        enum bb_alu_v488 op=(enum bb_alu_v488)i;
        uint64_t f=0x202, mask, ref_flags;
        const uint64_t expected=hardware(op,w,a,b,&ref_flags);
        const uint64_t value=alu_v488(op,w,a,b,&f,&mask);
        const uint64_t valid=op==BB_ADD||op==BB_SUB||op==BB_CMP?0x8d5:0x8c5;
        if(mask!=valid || ((f^ref_flags)&valid) || (op!=BB_CMP&&op!=BB_TEST&&value!=expected)) {
            fprintf(stderr,"arithmetic mismatch: width=%u op=%u\n",w,i);return 0;
        }
    }
    return 1;
}
#endif
int main(void) {
#if defined(__x86_64__) && (defined(__clang__) || defined(__GNUC__))
    const uint64_t values[]={0,1,15,16,127,128,255,256,0x7fffffff,0x80000000,
        0xffffffff,UINT64_C(0x100000000),UINT64_C(0x7fffffffffffffff),
        UINT64_C(0x8000000000000000),UINT64_MAX};
    uint64_t seed=0x706f7274;
    for(unsigned w=32;w<=64;w+=32) {
        for(unsigned a=0;a<sizeof values/sizeof *values;++a)
            for(unsigned b=0;b<sizeof values/sizeof *values;++b)
                if(!verify(w,values[a],values[b]))return 1;
        for(unsigned i=0;i<4096;++i) {
            seed=seed*UINT64_C(6364136223846793005)+1;
            uint64_t a=seed;
            seed=seed*UINT64_C(6364136223846793005)+1;
            if(!verify(w,a,seed))return 1;
        }
    }
    puts("V489_X86_ARITHMETIC_ORACLE_PASS");
#else
    puts("V489_X86_ARITHMETIC_ORACLE_SKIPPED_NON_X86");
#endif
    return 0;
}
