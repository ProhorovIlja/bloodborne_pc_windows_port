/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ALU_V488_H
#define BB_ALU_V488_H
#include "leaf_v484.h"
enum bb_alu_v488 {BB_ADD,BB_OR,BB_AND,BB_SUB,BB_XOR,BB_CMP,BB_TEST};
static inline uint64_t alu_v488(enum bb_alu_v488 op,unsigned w,uint64_t a,uint64_t b,
        uint64_t *flags,uint64_t *valid) {
    const uint64_t mask=w==32?UINT32_MAX:UINT64_MAX, sign=UINT64_C(1)<<(w-1);
    a&=mask; b&=mask;
    uint64_t x, f=0;
    *valid=0x8d5;
    switch(op) {
    case BB_ADD:
        x=(a+b)&mask;
        f=(x<a) | ((~(a^b)&(a^x)&sign)?0x800:0) | ((a^b^x)&16);
        break;
    case BB_SUB: case BB_CMP:
        x=(a-b)&mask;
        f=(a<b) | (((a^b)&(a^x)&sign)?0x800:0) | ((a^b^x)&16);
        break;
    default:
        x=op==BB_OR ? a|b : op==BB_XOR ? a^b : a&b;
        *valid=0x8c5;
        break;
    }
    unsigned p=(unsigned)x&255;
    p^=p>>4;
    f|=(((0x9669u>>(p&15))&1u)<<2) | (!x?64:0) | ((x&sign)?128:0);
    *flags=(*flags & ~*valid)|f;
    return x;
}
int bb_alu_call_v488(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,struct bb_result_v484 *);
#endif
