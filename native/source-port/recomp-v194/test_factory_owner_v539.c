/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "factory_owner_v539.h"

struct trace { uint32_t code; unsigned count, first, last; int resume; };
static int inject(void *ctx,uint64_t slot,uint32_t *rc) {
    if (slot!=0x2008) return 0;
    *rc=((struct trace *)ctx)->code; return 1;
}
static int log_line(void *ctx,unsigned line) {
    struct trace *s=ctx;
    if (!s->count++) s->first=line;
    s->last=line; return s->resume;
}
int main(void) {
    unsigned char p[0x490]; memset(p,0xa5,sizeof p);
    struct bb_owner_v539 owner={0};
    if (bb_owner_seed_v539(&owner,p,sizeof p,0x1001,1,2,3) || owner.body || p[0]!=0xa5) return 1;
    if (!bb_owner_seed_v539(&owner,p,sizeof p,0x1000,1,2,3) ||
        !owner.lock.live || p[0x480]!=1 || p[0x488] || p[0x48c]!=0xa5) return 2;
    unsigned char token[8]; bb_factory_put_v538(token,SHYT_RW_TOKEN_V414,8);
    if (memcmp(p+0x478,token,8) || bb_owner_seed_v539(&owner,p,sizeof p,0x1000,1,2,3) ||
        !shyt_rw_write_v414(&owner.lock) || shyt_rw_destroy_v414(&owner.lock) ||
        !shyt_rw_unlock_v414(&owner.lock) || !shyt_rw_destroy_v414(&owner.lock)) return 3;
    for (unsigned resume=0;resume<2;++resume) {
        unsigned char child[17]={0}; struct trace s={0x80020001,0,0,0,(int)resume};
        struct bb_child_result_v539 r=bb_child_init_v539(child,sizeof child,0x2000,&s,inject,log_line);
        if (r.status!=(resume?BB_CHILD_REJECTED:BB_CHILD_STOP) || r.guest_result ||
            s.count!=(resume?4u:1u) || s.first!=77 || s.last!=(resume?83u:77u) || child[16]!=resume) return 4;
        s=(struct trace){0x80020023,0,0,0,1}; child[16]=0;
        r=bb_child_init_v539(child,sizeof child,0x2000,&s,inject,log_line);
        if (r.status!=BB_CHILD_REJECTED || r.guest_result!=UINT32_MAX || s.count || child[16]) return 5;
    }
    return 0;
}
