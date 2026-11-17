/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLEANUP_CHAIN_V690_H
#define BB_CLEANUP_CHAIN_V690_H
#include "cleanup_resume_v688.h"

int bb_cleanup_tail(uint64_t, uint64_t, const uint64_t *, size_t, size_t,
                    uint64_t[6], uint8_t *, uint64_t *, size_t *);

struct bb_cleanup_state_v690 {
    uint64_t pc, nv[6];
    size_t consumed;
    uint8_t al;
};
enum bb_cleanup_status_v690 { BB_CLEANUP_MISS, BB_CLEANUP_RET, BB_CLEANUP_FATAL };

/* Frame and state are disjoint from the object and read-only to callbacks.
 * Canary is resolved by the caller. Only AL is exported; neither volatile
 * registers nor flags are part of this continuation contract. */
static inline enum bb_cleanup_status_v690 bb_cleanup_chain_v690(
    struct bb_cleanup_state_v690 *s, uint32_t value, void *object, size_t size,
    void *ctx, bb_cleanup_resolve_v687 resolve, uint64_t canary,
    const uint64_t *frame, size_t words, size_t bp) {
    if (!s || !value || !object || !frame) return BB_CLEANUP_MISS;
    const struct bb_cleanup_edge_v688 *edge = bb_cleanup_lookup_v688(s->pc);
    if (!edge) return BB_CLEANUP_MISS;
    struct bb_cleanup_state_v690 out = *s;
    /* Stage the pure epilogue before any callback. Commit only after the
     * prefix succeeds. On FATAL the original still performed cleanup. */
    out.al = 0;
    if (edge->result_in_r14) out.nv[4] = 0;
    int status = bb_cleanup_tail(edge->next,canary,frame,words,bp,
                                 out.nv,&out.al,&out.pc,&out.consumed);
    if (status != BB_CLEANUP_RET && status != BB_CLEANUP_FATAL) return BB_CLEANUP_MISS;
    uint64_t ignored_pc, ignored_r14 = s->nv[4];
    uint32_t ignored_eax = 0;
    unsigned ignored_defined;
    if (!bb_cleanup_resume_v688(s->pc,value,object,size,ctx,resolve,
            &ignored_pc,&ignored_r14,&ignored_eax,&ignored_defined)) return BB_CLEANUP_MISS;
    *s = out;
    return (enum bb_cleanup_status_v690)status;
}
#endif
