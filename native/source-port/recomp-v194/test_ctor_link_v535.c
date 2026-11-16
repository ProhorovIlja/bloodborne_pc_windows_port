/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ctor_link_v535.h"
struct state { uint64_t link[4]; unsigned reads, diagnostics, writes; int resume; };
static int read_next(void *x,uint64_t a,uint64_t *out) {
    struct state *s=x; ++s->reads;
    if (a>=4) return 0;
    *out=s->link[a]; return 1;
}
static int diag(void *x) { struct state *s=x; ++s->diagnostics; return s->resume; }
static int write_next(void *x,uint64_t a,uint64_t v) {
    struct state *s=x; ++s->writes;
    if (a!=1) return 0;
    s->link[a]=v; return 1;
}
int main(void) {
    const struct { uint64_t head, a, b, expected; unsigned reads, diags, writes;
        int resume; enum bb_link_status_v535 status; } cases[]={
        {0,0,0,99,0,0,1,0,BB_LINK_OK},
        {2,3,0,99,2,0,1,0,BB_LINK_OK},
        {1,0,0,99,0,1,1,1,BB_LINK_OK},
        {2,3,1,99,2,1,0,0,BB_LINK_DIAGNOSTIC},
        {2,3,2,99,3,0,0,0,BB_LINK_LIMIT},
        {2,8,0,99,2,0,0,0,BB_LINK_MISS}
    };
    for (size_t i=0;i<sizeof cases/sizeof *cases;++i) {
        struct state s={{0,cases[i].expected,cases[i].a,cases[i].b},0,0,0,cases[i].resume};
        if (bb_ctor_link_v535(1,cases[i].head,3,&s,read_next,diag,write_next)!=cases[i].status ||
            s.reads!=cases[i].reads || s.diagnostics!=cases[i].diags || s.writes!=cases[i].writes ||
            s.link[1]!=(s.writes?cases[i].head:cases[i].expected)) return (int)i+1;
    }
    return 0;
}
