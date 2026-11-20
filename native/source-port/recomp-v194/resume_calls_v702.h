/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_CALLS_V702_H
#define BB_RESUME_CALLS_V702_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct bb_calls702 {
    void *ctx;
    void (*restore)(void *, uint64_t, unsigned char *, uint64_t);
    int (*invoke)(void *, unsigned, unsigned);
    const uint64_t *(*guard)(void *);
    void (*cleanup)(void *, const uint64_t *);
};
struct bb_state702 { uint64_t pc, nv[6]; size_t used; unsigned al; };
enum bb_result702 { BB_MISS702, BB_RET702, BB_FATAL702, BB_STOP702 };

/* Native providers own pointer resolution. A late miss is terminal because
 * restore may have changed state. Frame/state and object must be disjoint;
 * the captured guard pointer must remain valid through cleanup. */
static inline enum bb_result702 bb_resume_calls702(struct bb_state702 *s,
        uint32_t value, unsigned char *obj, size_t bytes,
        const uint64_t *frame, size_t words, const struct bb_calls702 *c) {
    if (!s || s->pc != UINT64_C(0x23a510a) || !value || !obj || bytes < 0x1a1 ||
        !frame || words < 1054 || !c || !c->restore || !c->invoke || !c->guard || !c->cleanup)
        return BB_MISS702;
    c->restore(c->ctx, frame[5], obj+0x10, 0);
    if (!c->invoke(c->ctx, 0x68, 0)) return BB_STOP702;
    obj[0x1a0] = 0;
    const uint64_t *guard = c->guard(c->ctx);
    if (!guard) return BB_STOP702;
    c->cleanup(c->ctx, frame+526);
    s->al=0;
    if (*guard != frame[1046]) {
        s->pc=UINT64_C(0x2bbe4f8); s->used=0;
        return BB_FATAL702;
    }
    const unsigned order[]={0,2,3,4,5,1};
    for (size_t i=0;i<6;++i) s->nv[order[i]]=frame[1047+i];
    s->pc=frame[1053]; s->used=1054;
    return BB_RET702;
}
#endif
