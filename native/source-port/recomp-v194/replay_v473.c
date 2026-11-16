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
struct bb_patch_v474 { size_t offset; uint64_t value; };
#ifdef V475_PREPARED
int bb_data_init_v474(unsigned char *,size_t,const unsigned char *,size_t,const struct bb_patch_v474 *,size_t);
#endif
#ifdef V477_READONLY
#include "ro_v477.h"
struct bb_ro_string_v477 { uint64_t address; size_t length; unsigned width; };
#endif
#include V473_PLAN
#ifndef V475_PREPARED
#define STATE_SIZE (sizeof(initial))
#endif
#define N(a) (sizeof(a)/sizeof(*(a)))
_Static_assert(N(plan)>0 && N(plan)<=65536 && N(pool)>=16 && STATE_SIZE>=16 && STATE_SIZE<=16777216,"bounded plan");
static unsigned char memory[STATE_SIZE+2];
int native_guarded_leaf_v463(unsigned char *,size_t,size_t,uint64_t);
int native_startup_copy_v470(const struct startup_copy_v470 *,size_t,const unsigned char *,size_t,unsigned char *,size_t,unsigned char [32]);
int native_stores_v472(const struct store_v472 *,size_t,const unsigned char *,size_t,unsigned char *,size_t,uint64_t,uint64_t *,unsigned char [32]);
#ifdef V477_READONLY
static struct store_v472 resolved[N(plan)][6];
static int prepare_ro(void) {
    struct bb_ro_v476 view={0};
    if (!bb_ro_bind_v476(&view,ro_rows,N(ro_rows),pool,N(pool))) return 0;
    for (size_t i=0;i<N(ro_strings);++i) {
        const struct bb_ro_string_v477 *s=ro_strings+i;
        size_t n;
        if (s->width==1) {
            if (!bb_ro_strlen_v476(&view,s->address,&n)) return 0;
        } else if (s->width==2) {
            if (!bb_ro_u16len_v477(&view,s->address,&n)) return 0;
        } else return 0;
        if (n!=s->length) return 0;
    }
    for (size_t i=0;i<N(plan);++i) {
        const struct row *r=plan+i;
        for (unsigned j=0;j<r->n;++j) {
            resolved[i][j]=r->ops[j];
            if (r->kind && r->ops[j].width==16 &&
                !bb_ro_offset_v477(&view,r->ops[j].src,16,&resolved[i][j].src)) return 0;
        }
    }
    return 1;
}
#endif
static int validate(void) {
    unsigned prev=0;
    for (size_t i=0;i<N(plan);++i) {
        const struct row *r=plan+i;
        if (r->ordinal<=prev || r->ordinal>65536 || r->kind>2) return 0;
        prev=r->ordinal;
        if (!r->kind && (r->n!=1 || !r->address || r->address%8 || r->ops[0].width!=16)) return 0;
        if (r->kind==1 && ((r->n!=1 && r->n!=3 && r->n!=4) || r->address)) return 0;
        if (r->kind==2 && (r->n!=1 && r->n!=4 && r->n!=6)) return 0;
        for (unsigned j=0;j<r->n;++j) {
            const struct store_v472 *s=r->ops+j;
            const unsigned w=s->width;
            if (w!=16 && (r->kind!=2 || (w!=2 && w!=4) || j==0 || j+1!=r->n ||
                          (w==2 && s->immediate>UINT16_MAX))) return 0;
            if (s->dst>STATE_SIZE-w || (w==16 && (s->dst%16 || s->src%16
#ifndef V477_READONLY
                || s->src>N(pool)-16
#endif
                ))) return 0;
        }
    }
    return 1;
}
static void hex(const unsigned char *p,size_t n) {
    for (size_t i=0;i<n;++i) printf("%02x",(unsigned)p[i]);
}
int main(void) {
    if (!validate()) return 2;
#ifdef V477_READONLY
    if (!prepare_ro()) return 6;
#endif
    unsigned char *state=memory+1;
    memory[0]=0xa5; memory[STATE_SIZE+1]=0x5a;
#ifdef V475_PREPARED
    if (!bb_data_init_v474(state,STATE_SIZE,initial,INITIAL_SIZE,patches,PATCH_COUNT)) return 5;
#else
    memcpy(state,initial,N(initial));
#endif
    for (size_t i=0;i<N(plan);++i) {
        const struct row *r=plan+i;
#ifdef V477_READONLY
        unsigned char local_pool[96];
        struct store_v472 ops[6];
        for (unsigned j=0;j<r->n;++j) {
            ops[j]=resolved[i][j];
            if (r->kind && ops[j].width==16) {
                memcpy(local_pool+16*j,pool+ops[j].src,16);
                ops[j].src=16*j;
            }
        }
        const unsigned char *copy_pool=local_pool;
        const size_t copy_size=sizeof local_pool;
#else
        const struct store_v472 *ops=r->ops;
        const unsigned char *copy_pool=pool;
        const size_t copy_size=N(pool);
#endif
        unsigned char ymm[32];
        uint64_t rax=177;
        int status=1;
        if (!r->kind) {
            status=native_guarded_leaf_v463(state,STATE_SIZE,r->ops[0].dst,r->address);
            if (status<0) return 3;
        } else if (r->kind==1) {
            struct startup_copy_v470 steps[4];
            for (unsigned j=0;j<r->n;++j)
                steps[j]=(struct startup_copy_v470){ops[j].src,ops[j].dst};
            if (!native_startup_copy_v470(steps,r->n,copy_pool,copy_size,state,STATE_SIZE,ymm)) return 3;
        } else if (!native_stores_v472(ops,r->n,copy_pool,copy_size,state,STATE_SIZE,r->address,&rax,ymm)) return 3;
        if (memory[0]!=0xa5 || memory[STATE_SIZE+1]!=0x5a) return 3;
        printf("%u %d %" PRIu64,r->ordinal,status,rax);
        if (r->kind) { putchar(' '); hex(ymm,32); }
        for (unsigned j=0;j<r->n;++j) { putchar(' '); hex(state+r->ops[j].dst,r->ops[j].width); }
        putchar('\n');
    }
    uint64_t fingerprint=UINT64_C(14695981039346656037);
    for (size_t i=0;i<STATE_SIZE;++i)
        fingerprint=(fingerprint^state[i])*UINT64_C(1099511628211);
    printf("FINAL %016" PRIx64 "\n",fingerprint);
    return fflush(stdout)==EOF?4:0;
}
