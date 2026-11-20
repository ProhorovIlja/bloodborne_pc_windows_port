/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_JUMP_RECORD_V514_H
#define BB_JUMP_RECORD_V514_H
#include <stdint.h>
#include <stddef.h>

struct bb_jump_v514 {
    uint64_t rip, rsp, rbx, rbp, r12, r13, r14, r15, rax;
    uint32_t mxcsr;
    uint16_t x87cw;
};

static inline uint64_t bb_jump_read_v514(const unsigned char *p, unsigned n) {
    uint64_t x=0;
    for (unsigned i=0;i<n;++i) x|=(uint64_t)p[i]<<(i*8);
    return x;
}

/* Decode the inspected PS4 libc record prefix. Does not restore signals,
 * write guest stack, validate a live continuation or modify host FP state. */
static inline int bb_jump_plan_v514(const unsigned char *buf, size_t n,
        uint64_t value, uint32_t current_mxcsr, uint32_t mxcsr_mask,
        struct bb_jump_v514 *out) {
    if (!buf || n<72 || !out) return 0;
    const uint32_t saved=(uint32_t)bb_jump_read_v514(buf+68,4);
    const uint32_t merged=(saved & ~UINT32_C(63)) | (current_mxcsr & 63);
    if (merged & ~mxcsr_mask) return 0;
    const struct bb_jump_v514 candidate={
        bb_jump_read_v514(buf,8),bb_jump_read_v514(buf+16,8),
        bb_jump_read_v514(buf+8,8),bb_jump_read_v514(buf+24,8),
        bb_jump_read_v514(buf+32,8),bb_jump_read_v514(buf+40,8),
        bb_jump_read_v514(buf+48,8),bb_jump_read_v514(buf+56,8),value?value:1,
        merged,(uint16_t)bb_jump_read_v514(buf+64,2)
    };
    *out=candidate;
    return 1;
}
#endif
