/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "owner_registry_v540.h"

struct fixture { unsigned char data[48], once; unsigned calls, reject; };
static unsigned char arena[0x100008];
static int alloc(void *ctx,uint64_t self,size_t bytes,size_t align,struct bb_registry_block_v540 *out) {
    struct fixture *f=ctx;
    if (self!=0x1458 || bytes!=40 || align!=8 || f->once!=1 || f->calls++) return 0;
    if (f->reject) return 0;
    *out=(struct bb_registry_block_v540){f->data,40,0x6000};
    return 1;
}
int main(void) {
    for (unsigned reject=0;reject<2;++reject) {
        struct bb_owner_v539 owner={0}; unsigned char body[0x490];
        struct fixture f={.reject=reject};
        memset(body,0xa5,sizeof body); memset(arena,0xa5,sizeof arena); memset(f.data,0xa5,sizeof f.data);
        if (!bb_owner_seed_v539(&owner,body,sizeof body,0x1000,1,2,3)) return 1;
        if (bb_owner_registry_v540(&owner,0x1008,&f.once,arena,0x800000,&f,alloc)!=BB_REGISTRY_INVALID || f.once || f.calls) return 2;
        if (bb_owner_registry_v540(&owner,0x1000,&f.once,arena,0x800000,&f,alloc)!=
                (reject?BB_REGISTRY_ALLOC:BB_REGISTRY_SEEDED) || f.calls!=1 || f.once!=1) return 3;
        if (body[0x489]!=16 || body[0x468] || body[0x469]!=(reject?0:0x60) ||
            body[0x48c]!=0xa5 || arena[0]!=0xa5 || arena[8]==0xa5 || arena[0x100000]!=0xa5 ||
            f.data[0]!=0xa5 || f.data[8]!=(reject?0xa5:0) || f.data[33]!=(reject?0xa5:0x10) ||
            f.data[40]!=0xa5) return 4;
        if (bb_owner_registry_v540(&owner,0x1000,&f.once,arena,0x800000,&f,alloc)!=BB_REGISTRY_ALREADY ||
            f.calls!=1 || !shyt_rw_destroy_v414(&owner.lock)) return 5;
    }
    return 0;
}
