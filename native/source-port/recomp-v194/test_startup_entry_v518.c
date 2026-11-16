/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "startup_entry_v518.h"
#include <string.h>

struct state { uint64_t trace[11]; size_t n; uint32_t result; };
static void push(void *p,uint64_t v) { struct state *s=p; if (s->n<11) s->trace[s->n++]=v; }
static void env(void *p,uint64_t a,uint64_t b) { push(p,1); push(p,a); push(p,b); }
static void reg(void *p,uint64_t a) { push(p,a); }
static void init(void *p) { push(p,2); }
static uint32_t run(void *p,uint32_t a,uint64_t b,uint64_t c) {
    push(p,a); push(p,b); push(p,c); return ((struct state *)p)->result;
}
static void ret(void *p,uint32_t r) { push(p,r); }

int main(void) {
    const struct bb_entry_ops_v518 ops={env,reg,init,run,ret,ret};
    unsigned char v[8]={0x78,0x56,0x34,0x92,0xff,0xff,0xff,0xff};
    struct state s={.result=UINT32_MAX};
    if (bb_entry_v518(&ops,&s,v,7,100,200,300)!=BB_ENTRY_INVALID_V518 || s.n) return 1;
    if (bb_entry_v518(&ops,&s,v,8,UINT64_MAX-7,200,300)!=BB_ENTRY_INVALID_V518 || s.n) return 2;
    if (bb_entry_v518(&ops,&s,v,8,100,200,300)!=BB_ENTRY_EXIT_RETURNED_V518) return 3;
    const uint64_t want[]={1,100,200,200,300,2,UINT32_C(0x92345678),108,0,UINT32_MAX,UINT32_MAX};
    return s.n!=11 || memcmp(s.trace,want,sizeof want);
}
