/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "factory_seed_v538.h"
struct fixture { unsigned char *p; unsigned calls; int ok; };
static int child(void *ctx,uint64_t va) {
    struct fixture *s=ctx;
    ++s->calls;
    if (va!=0x1470 || s->p[0x470]!=3 || s->p[0x488]!=0xa5) return 0;
    s->p[0x478]=0x42;
    return s->ok;
}
int main(void) {
    for (int i=0;i<2;++i) {
        unsigned char p[0x490]; memset(p,0xa5,sizeof p);
        struct fixture s={p,0,i};
        if (bb_factory_seed_v538(p,sizeof p,0x1001,1,2,3,child,&s) ||
            bb_factory_seed_v538(p,0x48b,0x1000,1,2,3,child,&s) || s.calls || p[0]!=0xa5) return 1;
        if (bb_factory_seed_v538(p,sizeof p,0x1000,1,2,3,child,&s)!=i || s.calls!=1) return 2;
        for (size_t j=0;j<0x440;++j) if (p[j]) return 3;
        if (p[0x440]!=1 || p[0x448]!=0xa5 || p[0x450] || p[0x451]!=0xa5 ||
            p[0x458]!=2 || p[0x460] || p[0x461]!=0x10 || p[0x468] ||
            p[0x470]!=3 || p[0x478]!=0x42 || p[0x480] ||
            p[0x488]!=(i?0:0xa5) || p[0x48b]!=(i?0:0xa5) || p[0x48c]!=0xa5) return 4;
    }
    return 0;
}
