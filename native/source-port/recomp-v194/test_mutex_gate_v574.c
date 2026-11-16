/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "mutex_gate_v574.h"
#include <string.h>
struct fixture { unsigned char *p; unsigned trace; int acq, rc; unsigned char probe; };
static int acquire(void *v,unsigned char *p) {
    struct fixture *f=v;
    f->trace=f->trace*10+(p==f->p+32?1:9);
    return f->acq;
}
static void release(void *v,unsigned char *p) {
    struct fixture *f=v;
    f->trace=f->trace*10+(p==f->p+32 && !f->p[31]?2:9);
    *p=1;
}
static unsigned char probe(void *v,unsigned char *p) {
    struct fixture *f=v;
    f->trace=f->trace*10+(p==f->p && p[0]==0x88 && p[7]==0x11 && !p[16]?3:9);
    return f->probe;
}
static int init(void *v,unsigned char *p) {
    struct fixture *f=v;
    f->trace=f->trace*10+(p==f->p+8?4:9);
    *p=0x5a;
    return f->rc;
}
int main(void) {
    unsigned char p[40], before[40];
    struct fixture f={p,0,1,0,0};
    const struct bb_mutex_calls_v574 calls={acquire,release,probe,init};
    const struct bb_mutex_gate_v574 x={0,31,32,UINT64_C(0x1122334455667788)};
    memset(p,0xa5,sizeof p);
    p[32]=0;
    if (!bb_mutex_gate_v574(p,sizeof p,x,&calls,&f) || f.trace!=1234 ||
        p[31]!=1 || p[32]!=1 || p[16]!=1 || p[8]!=0x5a || p[17]!=0xa5) return 1;
    memcpy(before,p,sizeof p);
    f.trace=0;
    if (!bb_mutex_gate_v574(p,sizeof p,x,&calls,&f) || f.trace ||
        memcmp(before,p,sizeof p)) return 2;
    p[31]=0;
    f.rc=-1;
    if (!bb_mutex_gate_v574(p,sizeof p,x,&calls,&f) || f.trace!=34 ||
        p[31]!=1 || p[16]!=0) return 3;
    p[31]=0;
    f.trace=0;
    f.probe=0xff;
    if (!bb_mutex_gate_v574(p,sizeof p,x,&calls,&f) || f.trace!=3 ||
        p[31]!=1 || p[16]!=0) return 4;
    memcpy(before,p,sizeof p);
    if (bb_mutex_gate_v574(p,sizeof p,(struct bb_mutex_gate_v574){0,16,32,1},&calls,&f) ||
        bb_mutex_gate_v574(p,32,x,&calls,&f) || f.trace!=3 || memcmp(before,p,sizeof p)) return 5;
    return 0;
}
