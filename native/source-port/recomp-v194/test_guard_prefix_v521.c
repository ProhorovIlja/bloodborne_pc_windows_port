/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "guard_prefix_v521.h"
#include <string.h>
struct state { unsigned char *rw; unsigned seen; int fail; };
static int hook(void *p, enum bb_hook_v521 k, uint64_t a, uint32_t *r) {
    struct state *s=p;
    if (k!=s->seen++ || (k<2 ? a!=103 : a!=(k==2?112:120))) return 0;
    if ((int)k==s->fail) return 0;
    if (k==BB_RELEASE_V521) s->rw[2]=1;
    *r=k==BB_ACQUIRE_V521 ? 256u : k==BB_TEST_V521 ? 256u : 0;
    return 1;
}
int main(void) {
    unsigned char rw[48]={0}, old[48];
    struct state s={rw,0,-1}; rw[3]=9;
    if (!bb_guard_prefix_v521(rw,48,101,2,3,9,0x1234,hook,&s) || s.seen!=4 ||
        rw[2]!=1 || rw[3]!=1 || rw[11]!=0x34 || rw[12]!=0x12 || rw[27]!=1) return 1;
    memcpy(old,rw,sizeof rw);
    if (!bb_guard_prefix_v521(rw,48,101,2,3,9,0x1234,hook,&s) || s.seen!=4 ||
        bb_guard_prefix_v521(rw,48,101,11,3,9,0x1234,hook,&s) ||
        bb_guard_prefix_v521(rw,48,UINT64_MAX-47,2,3,9,0x1234,hook,&s) ||
        memcmp(old,rw,sizeof rw)) return 2;
    rw[2]=0; s.seen=0; s.fail=BB_RELEASE_V521;
    if (bb_guard_prefix_v521(rw,48,101,2,3,9,0x1234,hook,&s) || s.seen!=2 || rw[3]!=0) return 3;
    return 0;
}
