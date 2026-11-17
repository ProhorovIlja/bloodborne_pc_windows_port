/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_DISPATCH_V685_H
#define BB_RESUME_DISPATCH_V685_H
#include "resume_chain_v677.h"

int bb_guarded_resume(uint64_t, uint32_t *, uint64_t, const uint64_t *, size_t,
                      size_t, uint64_t[6], uint64_t *, uint64_t *);
/* Generated metadata; 0 means the site is not a guarded resume. */
size_t bb_guarded_words(uint64_t pc);
enum bb_dispatch_v685 { BB_DISPATCH_MISS, BB_DISPATCH_RET, BB_DISPATCH_FATAL };

/* No fallback. FATAL reports the import edge without calling it. The caller
 * resolves the TLS and guard, and supplies a frame relative to saved RSP. */
static inline enum bb_dispatch_v685 bb_dispatch_resume_v685(
    struct bb_resume_state_v677 *s, uint32_t value, uint32_t *tls,
    uint64_t tls_addr, uint64_t guard, const uint64_t *frame, size_t words, size_t bp) {
    if (!s || !value || !tls || !frame) return BB_DISPATCH_MISS;
    size_t count = bb_guarded_words(s->pc);
    if (!count)
        return bb_resume_chain_v677(s,value,tls,tls_addr,frame,words) == BB_RESUME_OK_V677
            ? BB_DISPATCH_RET : BB_DISPATCH_MISS;
    if (words < count) return BB_DISPATCH_MISS;
    struct bb_resume_state_v677 next = *s;
    uint32_t next_tls = *tls;
    int result = bb_guarded_resume(next.pc,&next_tls,guard,frame,words,bp,
                                  next.nonvolatile,&next.rax,&next.pc);
    if (result != BB_DISPATCH_RET && result != BB_DISPATCH_FATAL) return BB_DISPATCH_MISS;
    next.consumed = result == BB_DISPATCH_RET ? count : 0;
    *s = next;
    *tls = next_tls;
    return (enum bb_dispatch_v685)result;
}
#endif
