/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "init_walk_v520.h"
struct state { uint64_t a[6], log[6]; size_t n; uint64_t miss; };
static int rd(void *p,size_t i,uint64_t *out) {
    struct state *s=p;
    if (i%8 || i/8>=6) return 0;
    *out=s->a[i/8]; return 1;
}
static int call(void *p,uint64_t v) {
    struct state *s=p;
    if (v==s->miss || s->n>=6) return 0;
    s->log[s->n++]=v;
    if (v==3) s->a[2]=9;
    return 1;
}
int main(void) {
    struct state s={{UINT64_MAX,8,0,3,4,100},{0},0,0};
    struct bb_init_result_v520 r=bb_init_walk_v520(&s,rd,call,32,100,40,24,0);
    if (r.status!=BB_INIT_OK_V520 || r.slot || r.calls!=3 || s.n!=3 ||
        s.log[0]!=3 || s.log[1]!=9 || s.log[2]!=8) return 1;
    s.n=0; s.a[5]=101; s.miss=9;
    r=bb_init_walk_v520(&s,rd,call,32,100,40,24,0);
    if (r.status!=BB_INIT_MISS_V520 || r.slot!=16 || r.calls!=2 || s.n!=2 ||
        s.log[0]!=4 || s.log[1]!=3) return 2;
    s.n=0; s.a[0]=0; s.a[5]=100; s.a[1]=0; s.a[3]=0; s.a[2]=0;
    r=bb_init_walk_v520(&s,rd,call,32,100,40,24,0);
    return r.status!=BB_INIT_LAYOUT_V520 || r.slot || r.calls || s.n;
}
