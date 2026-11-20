/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ctor_route_v524.h"
#include <string.h>
struct fixture { unsigned char *rw; unsigned calls; };
static int hook(void *ctx,enum bb_hook_v521 op,uint64_t addr,uint32_t *r) {
    struct fixture *f=ctx;
    if ((unsigned)op!=f->calls++ || addr!=(op<2?32u:op==BB_TEST_V521?40u:48u)) return 0;
    if (op==BB_RELEASE_V521) f->rw[0]=1;
    *r=op==BB_ACQUIRE_V521;
    return 1;
}
int main(void) {
    unsigned char rw[80]={0},before[80];
    struct fixture f={rw,0};
    struct bb_ctor_route_v524 p={32,100,102,104,32,0,1,8,40};
    memcpy(before,rw,sizeof rw);
    if (bb_ctor_route_v524(rw,sizeof rw,&p,hook,&f) || f.calls || memcmp(before,rw,sizeof rw)) return 1;
    rw[40]=104;
    if (!bb_ctor_route_v524(rw,sizeof rw,&p,hook,&f) || f.calls!=4 ||
        rw[0]!=1 || rw[1]!=1 || rw[8]!=102 || rw[24]!=1 || rw[32]!=100) return 2;
    if (!bb_ctor_route_v524(rw,sizeof rw,&p,hook,&f) || f.calls!=4) return 3;
    rw[24]=0;
    if (bb_ctor_route_v524(rw,sizeof rw,&p,hook,&f) || f.calls!=4) return 4;
    p.predicate_slot=32; p.predicate=100;
    if (bb_ctor_route_v524(rw,sizeof rw,&p,hook,&f) || f.calls!=4) return 5;
    return 0;
}
