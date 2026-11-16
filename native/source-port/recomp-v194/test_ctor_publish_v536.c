/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ctor_publish_v536.h"
#include <string.h>
struct probe { unsigned calls; uint32_t bits; int resume; };
static int source(void *x,uint64_t *out) {
    struct probe *p=x; p->calls=p->calls*10+1; *out=64; return 1;
}
static int flags(void *x,uint64_t owner,uint32_t *out) {
    struct probe *p=x; p->calls=p->calls*10+2; *out=p->bits; return owner==72;
}
static int diag(void *x) { struct probe *p=x; p->calls=p->calls*10+3; return p->resume; }
int main(void) {
    const struct bb_publish_layout_v536 layout={0x1000,1,2,8,25,8,0};
    for (unsigned i=0;i<4;++i) {
        unsigned char rw[120]; memset(rw,0xa5,sizeof rw);
        bb_publish_store_v536(rw,i==3?77:0);
        bb_publish_store_v536(rw+8,i==1?72:0);
        struct probe p={0,i==1?0:32,i!=2};
        if (i==2) p.bits=0;
        uint64_t out=99;
        const enum bb_publish_status_v536 r=bb_ctor_publish_v536(rw,sizeof rw,&layout,&p,source,flags,diag,&out);
        if (i==3) { if (r!=BB_PUBLISH_OK || out!=77 || p.calls || rw[32]!=0xa5) return 4; }
        else if (i==2) {
            if (r!=BB_PUBLISH_DIAG || out!=99 || p.calls!=123 || bb_read64_v524(rw) ||
                bb_read64_v524(rw+32)!=1 || bb_read64_v524(rw+8)!=72 || rw[64]!=0xa5) return 3;
        } else if (r!=BB_PUBLISH_OK || out!=0x1020 || p.calls!=(i==1?23u:12u) ||
            bb_read64_v524(rw)!=out || bb_read64_v524(rw+32)!=2 ||
            bb_read64_v524(rw+56)!=UINT64_C(0xa5a5a5a5a5a5a5a5) ||
            bb_read64_v524(rw+88)!=72 || bb_read64_v524(rw+104) || rw[112]!=0xa5) return 1;
    }
    return 0;
}
