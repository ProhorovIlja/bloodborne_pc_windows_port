/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "unlock_v531.h"
struct state { uint32_t test, code; unsigned calls, miss; };
static int predicate(void *x,uint64_t a,uint32_t *r) {
    struct state *s=x;
    if (a!=16 || s->calls++ || s->miss==1) return 0;
    *r=s->test; return 1;
}
static int unlock(void *x,uint64_t a,uint32_t *r) {
    struct state *s=x;
    if (a!=24 || s->calls++!=1 || s->miss==2) return 0;
    *r=s->code; return 1;
}
int main(void) {
    const uint32_t rc[]={0,0x80020001,0x80020016,1,22,0x80020023};
    const uint32_t lines[]={0,0,192,197,197,197};
    for (unsigned j=0;j<4;++j) for (unsigned i=0;i<6;++i) {
        struct state s={j==3?0x100u:0x101u,rc[i],0,j<3?j:0};
        struct bb_unlock_result_v531 r=bb_unlock_v531(16,predicate,unlock,&s);
        const uint32_t line=j==3?153u:j?0u:lines[i];
        if (r.line!=line || r.status!=(j==1 || j==2?BB_UNLOCK_MISS:line?BB_UNLOCK_DIAG:BB_UNLOCK_RETURN) ||
            s.calls!=(j==1 || j==3?1u:2u)) return 1;
    }
    struct state s={0};
    return bb_unlock_v531(UINT64_MAX,predicate,unlock,&s).status!=BB_UNLOCK_MISS || s.calls;
}
