/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Synthetic startup replay. No retail code or descriptor data. */
#include "registry_once_v596.c"
#include "class_base_v602.c"
#include "class_register_v599.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

extern void *v603_allocate(void *,size_t);
extern void v603_release(void *,void *);
enum { N=140 };
typedef struct {
    BbRegistryOnce596 once;
    _Alignas(16) unsigned char owner[0x490], hdr[2][40];
    unsigned char *arena;
    BbClass90State597 child[N], base;
    void *cache;
    BbClass90Ops597 base_ops;
    struct bb_vector_block_v541 live[2];
    pthread_mutex_t gate, heap;
    pthread_rwlock_t areas;
    unsigned idx, fault, allocations, releases, factories, inits, diagnostics;
} Fixture;

static int gate_lock(void *v) { return pthread_mutex_lock(&((Fixture *)v)->gate); }
static int gate_unlock(void *v) { return pthread_mutex_unlock(&((Fixture *)v)->gate); }
static int rw_init(void *v,void *p) {
    Fixture *t=v; assert(p==t->owner+0x470); ++t->inits;
    return pthread_rwlock_init(&t->areas,NULL);
}
static int area_lock(void *v) { return pthread_rwlock_wrlock(&((Fixture *)v)->areas); }
static int area_unlock(void *v) { return pthread_rwlock_unlock(&((Fixture *)v)->areas); }
static void overlap(void *v) { (void)v; abort(); }
static BbArea593 *grow_area(void *v,size_t n) { (void)v;(void)n;abort(); }
static void free_area(void *v,BbArea593 *p) { (void)v;(void)p;abort(); }
static void take(void *p) {
    Fixture *t=(void *)((unsigned char *)p-(0x440+offsetof(Fixture,owner)));
    assert(!pthread_mutex_lock(&t->heap));
}
static void drop(void *p) {
    Fixture *t=(void *)((unsigned char *)p-(0x440+offsetof(Fixture,owner)));
    assert(!pthread_mutex_unlock(&t->heap));
}
static int ready(void *p) { return ((unsigned char *)p)[16]; }
static int init(void *p) { (void)p; return 0; }
static void *aligned(void *p,size_t n,size_t a) {
    assert(a==8); unsigned char *owner=(unsigned char *)p-0x458;
    take(owner+0x440);
    void *r=v603_allocate(owner,n);
    drop(owner+0x440);
    return r;
}
static const char token[]="synthetic factory";
static void context(void *v,const void *name,uint32_t line) {
    Fixture *t=v; assert(name==token && line==0xfb); ++t->diagnostics;
}
static int prepare(void *v) { (void)v; return 0; }
static void *factory(void *v) {
    Fixture *t=v;
    const BbRegistryHost596 host={t,gate_lock,gate_unlock,rw_init,1,2,3};
    const BbAreaOps593 ops={t,area_lock,area_unlock,overlap,grow_area,free_area};
    int status;
    ++t->factories;
    unsigned char *r=bb_registry_once_v596(&t->once,&host,t->owner,sizeof t->owner,t->arena,
       0x100000,ready,init,aligned,v603_allocate,take,drop,&ops,context,token,&status);
    assert(r==t->owner && status==1);
    return r+0x458;
}
static unsigned kind(void *v,void *p) {
    Fixture *t=v; assert(p==t->owner+0x458);
    return t->fault==3 && t->child[0].published?0:0x73;
}
static void diagnose(void *v,unsigned n) { (void)v; assert(n==0x3e); }
static int getbase(void *v,unsigned char **out) {
    Fixture *t=v; return bb_class_base_v602(&t->base,&t->cache,&t->base_ops,out);
}
static int field(void *v,uint64_t d,unsigned slot,uint64_t *out) {
    Fixture *t=v;
    assert(d==(uintptr_t)t->child[t->idx].descriptor);
    *out=slot<2?load594((unsigned char *)(uintptr_t)d+0x40+8*slot):(N-t->idx)*4+slot;
    return 1;
}
static int allocate(void *v,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    Fixture *t=v; assert(owner==(uintptr_t)t->owner);
    if (++t->allocations==t->fault) return 0;
    take(t->owner+0x440); unsigned char *p=v603_allocate(t->owner,n); drop(t->owner+0x440);
    if (!p) return 0;
    *b=(struct bb_vector_block_v541){p,n,(uintptr_t)p};
    t->live[n==0x4000?0:1]=*b;
    return 1;
}
static int release(void *v,uint64_t owner,uint64_t address) {
    Fixture *t=v; assert(owner==(uintptr_t)t->owner);
    take(t->owner+0x440); v603_release(t->owner,(void *)(uintptr_t)address); drop(t->owner+0x440);
    ++t->releases;
    return 1;
}
static int insert(void *v,unsigned char *d) {
    Fixture *t=v;
    t->cache=t->child[t->idx].allocator;
    for (unsigned i=0;i<2;++i)
        bb_arena_store_v527(t->hdr[i]+32,(uintptr_t)t->owner);
    const struct bb_class_ops_v599 o={t,field,allocate,release};
    struct bb_class_vector_v599 tables[2];
    for (unsigned i=0;i<2;++i)
        tables[i]=(struct bb_class_vector_v599){t->hdr[i],(uintptr_t)t->hdr[i],t->live[i]};
    return bb_class_register_v599(tables,tables+1,(uintptr_t)d,&o)!=BB_REG_OK;
}
static void run(unsigned fault) {
    Fixture *t=calloc(1,sizeof *t); assert(t);
    t->arena=malloc(0x100000); assert(t->arena);
    assert(!pthread_mutex_init(&t->gate,NULL) && !pthread_mutex_init(&t->heap,NULL));
    t->fault=fault;
    static const char *names[]={"synthetic-long","short","medium"};
    static const uint16_t wide[]={65,0};
    t->base_ops=(BbClass90Ops597){t,1,2,0,0,prepare,factory,kind,insert,NULL,diagnose};
    for (t->idx=0;t->idx<(fault?1u:N);++t->idx) {
        BbClass90Ops597 o=t->base_ops;
        o.ascii_name=(uintptr_t)names[t->idx%3]; o.wide_name=(uintptr_t)wide;
        t->child[t->idx].allocator=t->cache;
        int rc=bb_class90_checked_v603(t->child+t->idx,&o,getbase);
        assert(rc==(fault==3?-6:fault?-4:0));
        assert(parent597(t->child[t->idx].descriptor)==(fault?NULL:t->base.descriptor));
    }
    assert(t->factories==1 && t->inits==1 && t->diagnostics==1);
    assert((t->base.published!=NULL)==!fault);
    const size_t p=load594(t->hdr[0]+16)-load594(t->hdr[0]+8);
    const size_t s=load594(t->hdr[1]+16)-load594(t->hdr[1]+8);
    assert(p==(fault==1?0:fault?32:N*32) && s==(fault==3?64:fault?0:N*64));
    if (!fault) {
        assert(t->allocations==3 && t->releases==1);
        assert(load594(t->hdr[1]+24)-load594(t->hdr[1]+8)==768*16);
        for (unsigned i=0;i<2;++i) {
            unsigned char *b=t->live[i].data;
            size_t stride=i?16:32, key=i?0:24, n=(i?s:p)/stride;
            for (size_t k=1;k<n;++k) assert(load594(b+(k-1)*stride+key)<=load594(b+k*stride+key));
        }
    }
    assert(!pthread_rwlock_destroy(&t->areas));
    assert(!pthread_mutex_destroy(&t->gate) && !pthread_mutex_destroy(&t->heap));
    free(t->arena); free(t);
}
int main(void) {
    for (unsigned fault=0;fault<4;++fault) run(fault);
    puts("V603: one native factory, 140 descriptors, both registries, growth, 3 failure cases");
    return 0;
}
