/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <inttypes.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
struct startup_copy_v470 { size_t source, destination; };
struct store_v472 { size_t dst, src; uint32_t immediate; unsigned width; };
struct row { unsigned ordinal, kind, n; uint64_t address; struct store_v472 ops[6]; };
#ifndef V473_PLAN
#define V473_PLAN "fixture_v473.h"
#endif
#include V473_PLAN
#define N(a) (sizeof(a)/sizeof(*(a)))
_Static_assert(N(plan)>0 && N(plan)<=65536 && N(pool)>=16 && N(initial)>=16 && N(initial)<=16777216,"bounded plan");
static unsigned char memory[N(initial)+2];
int native_guarded_leaf_v463(unsigned char *,size_t,size_t,uint64_t);
int native_startup_copy_v470(const struct startup_copy_v470 *,size_t,const unsigned char *,size_t,unsigned char *,size_t,unsigned char [32]);
int native_stores_v472(const struct store_v472 *,size_t,const unsigned char *,size_t,unsigned char *,size_t,uint64_t,uint64_t *,unsigned char [32]);
static int validate(void) {
    unsigned prev=0;
    for (size_t i=0;i<N(plan);++i) {
        const struct row *r=plan+i;
        if (r->ordinal<=prev || r->ordinal>65536 || r->kind>2) return 0;
        prev=r->ordinal;
        if (!r->kind && (r->n!=1 || !r->address || r->address%8)) return 0;
        if (r->kind==1 && ((r->n!=1 && r->n!=3 && r->n!=4) || r->address)) return 0;
        if (r->kind==2 && (r->n!=1 && r->n!=4 && r->n!=6)) return 0;
        for (unsigned j=0;j<r->n;++j) {
            const struct store_v472 *s=r->ops+j;
            const unsigned w=s->width;
            if (w!=16 && (r->kind!=2 || (w!=2 && w!=4) || j==0 || j+1!=r->n ||
                          (w==2 && s->immediate>UINT16_MAX))) return 0;
            if (s->dst>N(initial)-w || (w==16 && (s->dst%16 || s->src%16 || s->src>N(pool)-16))) return 0;
        }
    }
    return 1;
}
static void hex(const unsigned char *p,size_t n) {
    for (size_t i=0;i<n;++i) printf("%02x",(unsigned)p[i]);
}
int main(void) {
    if (!validate()) return 2;
    unsigned char *state=memory+1;
    memory[0]=0xa5; memory[N(initial)+1]=0x5a;
    memcpy(state,initial,N(initial));
    for (size_t i=0;i<N(plan);++i) {
        const struct row *r=plan+i;
        unsigned char ymm[32];
        uint64_t rax=177;
        int status=1;
        if (!r->kind) {
            status=native_guarded_leaf_v463(state,N(initial),r->ops[0].dst,r->address);
            if (status<0) return 3;
        } else if (r->kind==1) {
            struct startup_copy_v470 steps[4];
            for (unsigned j=0;j<r->n;++j)
                steps[j]=(struct startup_copy_v470){r->ops[j].src,r->ops[j].dst};
            if (!native_startup_copy_v470(steps,r->n,pool,N(pool),state,N(initial),ymm)) return 3;
        } else if (!native_stores_v472(r->ops,r->n,pool,N(pool),state,N(initial),r->address,&rax,ymm)) return 3;
        if (memory[0]!=0xa5 || memory[N(initial)+1]!=0x5a) return 3;
        printf("%u %d %" PRIu64,r->ordinal,status,rax);
        if (r->kind) { putchar(' '); hex(ymm,32); }
        for (unsigned j=0;j<r->n;++j) { putchar(' '); hex(state+r->ops[j].dst,r->ops[j].width); }
        putchar('\n');
    }
    uint64_t fingerprint=UINT64_C(14695981039346656037);
    for (size_t i=0;i<N(initial);++i)
        fingerprint=(fingerprint^state[i])*UINT64_C(1099511628211);
    printf("FINAL %016" PRIx64 "\n",fingerprint);
    return fflush(stdout)==EOF?4:0;
}
