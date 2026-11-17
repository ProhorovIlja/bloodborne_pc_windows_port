/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "singleton_ctor_v576.h"
static int acquire(void *v,unsigned char *g) { (void)v; (void)g; return 1; }
static void release(void *v,unsigned char *g) { (void)v; *g=1; }
static unsigned char probe(void *v,unsigned char *o) { (void)v; return o[16]; }
static int init(void *v,unsigned char *m) { (void)v; *m=7; return 0; }
struct fixture { unsigned char *data; unsigned trace, mode; };
static int lock(void *v,unsigned char *m,int32_t wait) {
    struct fixture *f=v;
    if (m!=f->data || wait!=-1 || m[16]!=1) return 0;
    f->trace=f->trace*10+1;
    if (f->mode==2) { uintptr_t p=(uintptr_t)(f->data+72); memcpy(f->data+32,&p,8); }
    return f->mode!=3;
}
static int unlock(void *v,unsigned char *m) {
    struct fixture *f=v; f->trace=f->trace*10+3;
    return m==f->data;
}
static int construct(void *v,unsigned char *o,size_t n) {
    struct fixture *f=v; f->trace=f->trace*10+2;
    if (f->mode==1 || o!=f->data+64 || n!=16) return 0;
    memset(o,0xa5,n);
    return 1;
}
int main(void) {
    unsigned char b[80]={0};
    struct fixture f={b,0,0};
    struct bb_singleton_v576 x={{0,24,25,1},32,64,16,40};
    const struct bb_singleton_calls_v576 c={{acquire,release,probe,init},lock,unlock,construct};
    const unsigned want[]={123,123,13,1};
    for (unsigned mode=0;mode<4;++mode) {
        memset(b,0,sizeof b); f.trace=0; f.mode=mode;
        const int ok=mode==0 || mode==2;
        if (bb_singleton_ctor_v576(b,sizeof b,x,&c,&f)!=(ok?BB_SINGLETON_OK:BB_SINGLETON_STOP) ||
            f.trace!=want[mode] || b[40]!=(mode<2)) return 1;
        uintptr_t p=0; memcpy(&p,b+32,8);
        if (p!=(ok?(uintptr_t)(b+(mode==2?72:64)):0)) return 2;
        if (ok && (bb_singleton_ctor_v576(b,sizeof b,x,&c,&f)!=BB_SINGLETON_OK || f.trace!=want[mode])) return 3;
    }
    unsigned char before[80]; memcpy(before,b,sizeof b); x.guard=72;
    if (bb_singleton_ctor_v576(b,sizeof b,x,&c,&f)!=BB_SINGLETON_INVALID || memcmp(b,before,sizeof b)) return 4;
    return 0;
}
