/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ctor_register_v537.h"
struct fixture { unsigned calls, flags, links, resume; uint64_t next; };
static int source(void *x,uint64_t *a) {
    struct fixture *s=x; ++s->calls; *a=0x800; return 1;
}
static int flags(void *x,uint64_t a,uint32_t *bits) {
    struct fixture *s=x; if (a!=0x808) return 0;
    *bits=++s->flags==s->resume?0:32; return 1;
}
static int diag(void *x) { (void)x; return 0; }
static int read_next(void *x,uint64_t a,uint64_t *out) {
    (void)x; if (a!=0x1080) return 0; *out=0; return 1;
}
static int write_next(void *x,uint64_t a,uint64_t next) {
    struct fixture *s=x; if (a!=0x1020 || next!=0x1080) return 0;
    ++s->links; s->next=next; return 1;
}
int main(void) {
    const struct bb_publish_layout_v536 a={0x1000,1,2,8,32,16,0};
    const struct bb_publish_layout_v536 b={0x1000,3,4,8,128,16,8};
    const enum bb_register_v537 expected[]={BB_REGISTER_OK,BB_REGISTER_OBJECT,
        BB_REGISTER_HEAD,BB_REGISTER_LINK};
    for (unsigned i=0;i<4;++i) {
        unsigned char data[224]={0}; struct fixture s={0,0,0,i,0};
        if (bb_ctor_register_v537(data,sizeof data,&a,&b,&s,source,flags,diag,
                diag,i==3?0:1,read_next,write_next)!=expected[i] ||
            s.calls!=1 || s.flags!=(i==1?1u:2u) || s.links!=(i==0) ||
            bb_read64_v524(data)!=(i==1?0u:0x1020u) ||
            bb_read64_v524(data+8)!=(i==0 || i==3?0x1080u:0u)) return (int)i+1;
    }
    return 0;
}
