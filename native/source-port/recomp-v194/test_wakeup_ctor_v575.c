/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "wakeup_ctor_v575.h"
#include <string.h>
struct fixture { unsigned char *data; unsigned trace; int fail; };
static int acquire(void *p,unsigned char *g) {
    struct fixture *f=p;
    f->trace=f->trace*10+(g==f->data+41 && f->data[0]==0x77 ? 1 : 9);
    return 1;
}
static void release(void *p,unsigned char *g) {
    struct fixture *f=p;
    f->trace=f->trace*10+2;
    *g=1;
}
static unsigned char probe(void *p,unsigned char *o) {
    struct fixture *f=p;
    f->trace=f->trace*10+(o==f->data+8 && o[0]==0x66 ? 3 : 9);
    return o[16];
}
static int init(void *p,unsigned char *o) {
    struct fixture *f=p;
    f->trace=f->trace*10+(o==f->data+16 ? 4 : 9);
    return f->fail;
}
static void diagnostic(void *p) {
    struct fixture *f=p;
    f->trace=f->trace*10+5;
}
int main(void) {
    unsigned char data[48]={0}, before[48];
    struct fixture f={data,0,0};
    struct bb_wakeup_v575 x={{8,40,41,0x66},0,0x77};
    const struct bb_mutex_calls_v574 calls={acquire,release,probe,init};
    if (!bb_wakeup_ctor_v575(data,sizeof data,x,&calls,diagnostic,&f) ||
        f.trace!=12343 || data[24]!=1 || data[40]!=1 || data[41]!=1) return 1;
    f.trace=0;
    data[0]=0;
    if (!bb_wakeup_ctor_v575(data,sizeof data,x,&calls,diagnostic,&f) ||
        f.trace!=3 || data[0]!=0x77) return 2;
    memset(data,0,sizeof data);
    f.trace=0;
    f.fail=-1;
    if (!bb_wakeup_ctor_v575(data,sizeof data,x,&calls,diagnostic,&f) ||
        f.trace!=123435 || data[24] || data[40]!=1) return 3;
    memcpy(before,data,sizeof before);
    f.trace=0;
    x.published=8;
    if (bb_wakeup_ctor_v575(data,sizeof data,x,&calls,diagnostic,&f) ||
        f.trace || memcmp(before,data,sizeof before)) return 4;
    return 0;
}
