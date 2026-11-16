/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_OWNER_FACTORY_V552_H
#define BB_OWNER_FACTORY_V552_H
#include "singleton_v525.h"
#include "owner_finish_v551.h"

struct bb_owner_factory_v552 {
    struct bb_singleton_session_v533 publication;
    struct bb_owner_finish_v551 finish;
    int stopped;
};
/* One serialized startup controller. The bound layout is immutable. init
 * prepares the owner/RW lock; heap_mutex binds a separate lock after the
 * publication lock has been released. Published does not mean usable. */
static inline int bb_owner_factory_v552(struct bb_owner_factory_v552 *f,
        struct bb_owner_v539 *o,unsigned char *rw,size_t n,
        const struct bb_ctor_route_v524 *p,const struct bb_singleton_v525 *s,size_t inner,
        bb_call_v521 guard,int (*sync)(void *,uint64_t,uint64_t,uint32_t),
        int (*init)(void *,uint64_t),int (*heap_mutex)(void *,uint64_t),void *ctx,
        const struct bb_region_v478 *a,uint64_t heap_va,uint64_t arena_va,
        const struct bb_registry_tls_v548 *tls,const struct bb_registry_driver_v548 *d,
        int (*header)(void *,uint64_t,size_t,size_t,struct bb_registry_block_v540 *),
        int (*warn)(void *),uint64_t *out) {
    if (!f || f->stopped || !o || !s || !rw || n<8 || s->published>n-8 ||
        !heap_mutex || !out) return 0;
    uint64_t value=0;
    if (bb_singleton_once_v533(&f->publication,rw,n,p,s,guard,sync,init,ctx,&value,&inner)!=BB_SINGLETON_OK ||
        !value || value!=o->va || !o->body || !o->lock.live || value>UINT64_MAX-0x48c ||
        (f->finish.state==BB_FINISH_COLD && !heap_mutex(ctx,value+0x448)) ||
        bb_owner_finish_v551(&f->finish,o,a,heap_va,arena_va,tls,d,header,warn)!=BB_FINISH_READY) {
        f->stopped=1;
        return 0;
    }
    *out=value;
    return 1;
}
#endif
