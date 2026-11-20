/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_CHAIN_V677_H
#define BB_RESUME_CHAIN_V677_H
#include <stddef.h>
#include <stdint.h>

int bb_resume_branch(uint64_t, uint32_t, uint64_t *);
int bb_resume_block(uint64_t, uint64_t[3], uint64_t *, uint64_t *);
int bb_resume_return(uint64_t, uint32_t *, uint64_t, const uint64_t *,
                     size_t, uint64_t[6], uint64_t *, uint64_t *, size_t *);

struct bb_resume_state_v677 {
    uint64_t pc, rax;
    uint64_t nonvolatile[6]; /* RBX, RBP, R12, R13, R14, R15 */
    size_t consumed;
};
enum bb_resume_status_v677 {
    BB_RESUME_OK_V677, BB_RESUME_INPUT_V677, BB_RESUME_BRANCH_V677,
    BB_RESUME_BLOCK_V677, BB_RESUME_EPILOGUE_V677
};

/* Caller supplies a non-overlapping bounded frame and resolved TLS cell.
 * No guest instructions execute here. This returns a PC, not a transfer to
 * arbitrary code. Caller-clobbered flags are not exported across RET. */
static inline enum bb_resume_status_v677 bb_resume_chain_v677(
        struct bb_resume_state_v677 *state, uint32_t result, uint32_t *tls,
        uint64_t tls_addr, const uint64_t *frame, size_t words) {
    if (!state || !tls || !frame || !result) return BB_RESUME_INPUT_V677;
    struct bb_resume_state_v677 next = *state;
    uint32_t next_tls = *tls;
    uint64_t scratch_flags = 0, regs[3] = {
        next.nonvolatile[0], next.nonvolatile[4], next.nonvolatile[5]
    };
    if (!bb_resume_branch(next.pc,result,&next.pc)) return BB_RESUME_BRANCH_V677;
    if (!bb_resume_block(next.pc,regs,&scratch_flags,&next.pc)) return BB_RESUME_BLOCK_V677;
    next.nonvolatile[0]=regs[0];
    next.nonvolatile[4]=regs[1];
    next.nonvolatile[5]=regs[2];
    if (!bb_resume_return(next.pc,&next_tls,tls_addr,frame,words,next.nonvolatile,
                          &next.rax,&next.pc,&next.consumed)) return BB_RESUME_EPILOGUE_V677;
    *tls=next_tls;
    *state=next;
    return BB_RESUME_OK_V677;
}
#endif
