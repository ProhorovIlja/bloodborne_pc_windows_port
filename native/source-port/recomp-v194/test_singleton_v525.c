/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "singleton_v525.h"
struct state { unsigned steps; int ready, held; };
static int guard(void *ctx,enum bb_hook_v521 op,uint64_t addr,uint32_t *r) {
    (void)ctx; (void)op; (void)addr; (void)r; return 0;
}
static int sync(void *ctx,uint64_t id,uint64_t obj,uint32_t timeout) {
    struct state *s=ctx;
    if (obj!=40 || (s->held ? id!=2 || timeout : id!=1 || timeout!=UINT32_MAX)) return 0;
    ++s->steps; s->held=!s->held; return 1;
}
static int init(void *ctx,uint64_t addr) {
    struct state *s=ctx; ++s->steps; return s->held && s->ready && addr==88;
}
int main(void) {
    unsigned char rw[96]={1,1}; rw[8]=42; rw[24]=1; rw[32]=1; rw[40]=2;
    const struct bb_ctor_route_v524 p={32,0,42,0,0,0,1,8,0};
    const struct bb_singleton_v525 q={48,53,32,40,1,2};
    struct state s={0}; uint64_t out=99;
    rw[40]=3;
    if (bb_singleton_get_v525(rw,96,&p,&q,guard,sync,init,&s,&out)!=BB_SINGLETON_MISS || s.steps || out!=99) return 1;
    rw[40]=2;
    if (bb_singleton_get_v525(rw,96,&p,&q,guard,sync,init,&s,&out)!=BB_SINGLETON_MISS ||
        s.steps!=3 || s.held || rw[48] || out!=99) return 2;
    s.ready=1;
    if (bb_singleton_get_v525(rw,96,&p,&q,guard,sync,init,&s,&out)!=BB_SINGLETON_OK ||
        s.steps!=6 || s.held || rw[48]!=88 || out!=88) return 3;
    if (bb_singleton_get_v525(rw,96,&p,&q,guard,sync,init,&s,&out)!=BB_SINGLETON_OK ||
        s.steps!=6 || out!=88) return 4;
    return 0;
}
