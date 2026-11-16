/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "owner_registry_v540.h"
#include "registry_startup_v548.h"
#include "startup_memory_v478.h"

extern void *bb_engine_regular_heap_allocate_aligned_02485a60(void *,uint64_t,uint64_t);
extern void bb_engine_regular_heap_free_024858a0(void *,void *);
static _Alignas(16) unsigned char arena[0x100000];
/* Serialized test only. DLRegularHeap metadata is host-private; registry
 * references use the guest region. Free is only called with live blocks. */
struct fixture {
    struct bb_region_v478 span;
    uint64_t owner;
    unsigned char *body;
    pthread_mutex_t mutex;
    uint64_t live[3];
};
static enum bb_alloc_v548 get(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    struct fixture *f=x;
    if (owner!=f->owner || !n || pthread_mutex_lock(&f->mutex)) return BB_ALLOC_ERROR;
    size_t slot=0;
    while (slot<3 && f->live[slot]) ++slot;
    if (slot==3) { (void)pthread_mutex_unlock(&f->mutex); return BB_ALLOC_ERROR; }
    void *p=bb_engine_regular_heap_allocate_aligned_02485a60(f->body,n,8);
    if (!p) return pthread_mutex_unlock(&f->mutex)?BB_ALLOC_ERROR:BB_ALLOC_NO_SPACE;
    const uintptr_t addr=(uintptr_t)p, base=(uintptr_t)f->span.data;
    if (addr<base || n>f->span.size || addr-base>f->span.size-n) {
        (void)pthread_mutex_unlock(&f->mutex);
        return BB_ALLOC_ERROR;
    }
    *out=(struct bb_vector_block_v541){p,n,f->span.base+(addr-base)};
    f->live[slot]=out->va;
    return pthread_mutex_unlock(&f->mutex)?BB_ALLOC_ERROR:BB_ALLOC_OK;
}
static int put(void *x,uint64_t owner,uint64_t va) {
    struct fixture *f=x;
    unsigned char *p=bb_memory_at_v478(&f->span,va,1);
    if (owner!=f->owner || !p || (va&15) || pthread_mutex_lock(&f->mutex)) return 0;
    size_t slot=0;
    while (slot<3 && f->live[slot]!=va) ++slot;
    if (slot==3) { (void)pthread_mutex_unlock(&f->mutex); return 0; }
    bb_engine_regular_heap_free_024858a0(f->body,p);
    f->live[slot]=0;
    return !pthread_mutex_unlock(&f->mutex);
}
static int header(void *x,uint64_t self,size_t n,size_t align,struct bb_registry_block_v540 *out) {
    struct fixture *f=x; struct bb_vector_block_v541 b;
    if (self!=f->owner+0x458 || align!=8 || get(x,f->owner,n,&b)!=BB_ALLOC_OK) return 0;
    *out=(struct bb_registry_block_v540){b.data,b.size,b.va};
    return 1;
}
static int reserve(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    return get(x,owner,n,out)==BB_ALLOC_OK;
}
static int warn(void *x) { (void)x; return 0; }
static int run(uint64_t base,int preallocate) {
    _Alignas(16) unsigned char body[0x490]={0}; unsigned char once=0,tls[80]={0};
    struct bb_owner_v539 owner={0};
    struct fixture f={{base,sizeof arena,arena},base+0x200000,body,PTHREAD_MUTEX_INITIALIZER,{0}};
    const struct bb_registry_tls_v548 t={tls,sizeof tls,48,base+0x300000,0x9999,-24,-8,-48};
    const struct bb_registry_driver_v548 d={&f,get,put};
    if (!bb_owner_seed_v539(&owner,body,sizeof body,f.owner,1,2,3) ||
        bb_owner_registry_seed_v549(&owner,f.owner,(uintptr_t)body,&once,arena,(uintptr_t)arena,&f,header)!=BB_REGISTRY_SEEDED) return 1;
    const uint64_t hva=bb_vector_word_v541(body+0x468);
    unsigned char *h=bb_memory_at_v478(&f.span,hva,40);
    if (!h || (uintptr_t)h==hva || bb_vector_word_v541(h+32)!=f.owner ||
        bb_memory_at_v478(&f.span,base-1,1) || bb_memory_at_v478(&f.span,base+sizeof arena-1,2) ||
        put(&f,f.owner,base+sizeof arena)) return 2;
    if (preallocate && bb_vector_reserve_v541(h,40,hva,NULL,&f,reserve,put)!=BB_VEC_READY) return 3;
    for (unsigned i=0;i<65;++i) {
        const uint64_t lo=bb_vector_word_v541(h+8), cap=bb_vector_word_v541(h+24);
        struct bb_vector_block_v541 b={bb_memory_at_v478(&f.span,lo,(size_t)(cap-lo)),(size_t)(cap-lo),lo};
        const struct bb_registry_result_v548 r=bb_registry_startup_v548(&owner.lock,&t,h,40,hva,
            lo?&b:NULL,1+i,0x2000+32*i,16,warn,NULL,&d);
        if (!r.unlocked || r.insert!=BB_INSERT_OK || r.action.kind!=BB_TX_INVALID || tls[32]!=0xfb) return 4;
    }
    const uint64_t lo=bb_vector_word_v541(h+8), cap=bb_vector_word_v541(h+24);
    const unsigned char *p=bb_memory_at_v478(&f.span,lo,(size_t)(cap-lo));
    if (!p || (uintptr_t)p==lo || bb_vector_word_v541(h+16)-lo!=65*24 ||
        (cap-lo)!=(preallocate?72u:94u)*24) return 5;
    for (unsigned i=0;i<65;++i,p+=24) {
        if (bb_vector_word_v541(p)!=1+i || bb_vector_word_v541(p+8)!=0x2000+32*i ||
            bb_vector_word_v541(p+16)!=0x2010+32*i) return 6;
    }
    if (put(&f,f.owner,lo+16) || put(&f,f.owner+16,lo)) return 8;
    if (!put(&f,f.owner,lo) || !put(&f,f.owner,hva) ||
        put(&f,f.owner,lo) || put(&f,f.owner,hva) || bb_vector_word_v541(body+32) ||
        bb_vector_word_v541(body+24)!=bb_vector_word_v541(body+0x438) ||
        pthread_mutex_destroy(&f.mutex) || !shyt_rw_destroy_v414(&owner.lock)) return 7;
    return 0;
}
int main(void) {
    const uint64_t base[]={0x100000,0x100000000,UINT64_C(0x7fff00000000)};
    for (unsigned i=0;i<sizeof base/sizeof *base;++i)
        for (int p=0;p<2;++p) { int r=run(base[i],p); if (r) return r; }
    return 0;
}
