/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "owner_factory_v552.h"
static unsigned char arena[0x100000];
struct state {
    unsigned char rw[1024], body[0x490];
    struct bb_owner_v539 o;
    unsigned phase, mode;
};
static int guard(void *x,enum bb_hook_v521 op,uint64_t va,uint32_t *v) {
    struct state *t=x;
    if (op==BB_ACQUIRE_V521) { *v=1; return va==0x1000 || va==0x1002; }
    if (op==BB_RELEASE_V521) { t->rw[va-0x1000]=1; return 1; }
    *v=0;
    return va==(op==BB_TEST_V521?0x1010u:0x1018u);
}
static int sync_call(void *x,uint64_t id,uint64_t va,uint32_t timeout) {
    struct state *t=x;
    if (va!=0x1010) return 0;
    if (id==4 && timeout==UINT32_MAX && t->phase==0) { t->phase=1; return 1; }
    if (id==5 && !timeout && t->phase==2 && bb_read64_v524(t->rw+48)==0x1040) {
        t->phase=3;
        return t->mode!=1;
    }
    return 0;
}
static int seed(void *x,uint64_t va) {
    struct state *t=x;
    if (t->phase!=1 || !t->rw[2] || bb_read64_v524(t->rw+48)) return 0;
    t->phase=2;
    return bb_owner_seed_v539(&t->o,t->body,sizeof t->body,va,1,2,3);
}
static int mutex(void *x,uint64_t va) {
    struct state *t=x;
    if (t->phase!=3 || va!=0x1488) return 0;
    t->phase=4;
    return t->mode!=2;
}
static int head(void *x,uint64_t self,size_t n,size_t al,struct bb_registry_block_v540 *b) {
    struct state *t=x;
    if (t->phase!=4 || self!=0x1498 || n!=40 || al!=8) return 0;
    t->phase=5;
    *b=(struct bb_registry_block_v540){arena+0x100,40,0x200100};
    return 1;
}
static enum bb_alloc_v548 alloc(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    struct state *t=x;
    if (t->phase!=5 || owner!=0x1040 || n!=768) return BB_ALLOC_ERROR;
    t->phase=6;
    *b=(struct bb_vector_block_v541){arena+0x200,768,0x200200};
    return t->mode==3?BB_ALLOC_NO_SPACE:BB_ALLOC_OK;
}
static int release(void *x,uint64_t owner,uint64_t va) { (void)x; (void)owner; (void)va; return 0; }
static int warn(void *x) { (void)x; return 0; }
int main(void) {
    const struct bb_ctor_route_v524 p={.base=0x1000,.guard=0,.done=1,.storage=16,.vtable=6};
    const struct bb_singleton_v525 s={48,64,32,40,4,5};
    const struct bb_region_v478 a={0x200000,sizeof arena,arena};
    for (unsigned i=0;i<4;++i) {
        struct state t={.mode=i};
        struct bb_owner_factory_v552 f={0};
        unsigned char tls[80]={0};
        const struct bb_registry_tls_v548 l={tls,sizeof tls,48,0x400000,7,-24,-8,-48};
        const struct bb_registry_driver_v548 d={&t,alloc,release};
        bb_arena_store_v527(t.rw+32,4); bb_arena_store_v527(t.rw+40,5);
        const unsigned phase=i==1?3:i==2?4:6;
        for (unsigned pass=0;pass<2;++pass) {
            uint64_t out=99;
            if (bb_owner_factory_v552(&f,&t.o,t.rw,sizeof t.rw,&p,&s,2,guard,sync_call,seed,mutex,&t,
                 &a,0x1040,0x200000,&l,&d,head,warn,&out)!=(i==0) ||
                out!=(i?99u:0x1040u) || t.phase!=phase) return 1;
        }
        if (!i && (tls[32]!=0xfb || bb_read64_v524(arena+0x200)!=0x1498 ||
            bb_read64_v524(arena+0x210)!=0x300000)) return 2;
        if (!shyt_rw_destroy_v414(&t.o.lock)) return 3;
    }
    return 0;
}
