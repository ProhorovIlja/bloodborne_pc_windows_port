/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Unity unit: reuse the V593 implementation and ABI without a second copy.
 * Compile this unit instead of registry_area_v593.c when linking this adapter. */
#include "registry_area_v593.c"

static uintptr_t load594(const void *p) {
    uintptr_t v;
    memcpy(&v,p,sizeof v);
    return v;
}
static void store594(void *p,uintptr_t v) { memcpy(p,&v,sizeof v); }
static int held594(void *ctx) { (void)ctx; return 0; }

/* arena and owner are stable, disjoint, caller-owned buffers. The supplied
 * lock covers all metadata readers/writers. Growth callbacks must allocate
 * from arena, not overlap live objects, and not acquire that same lock. */
int bb_registry_bind_v594(unsigned char *owner,size_t owner_size,
                          unsigned char *arena,size_t arena_size,
                          const BbAreaOps593 *op,uintptr_t heap,
                          uintptr_t start,uintptr_t length) {
    if (!heap) return BB593_DUP;
    const uintptr_t a=(uintptr_t)arena, o=(uintptr_t)owner;
    if (sizeof(uintptr_t)!=8 || !owner || owner_size<0x48c || !arena || arena_size<0x28 ||
        a>UINTPTR_MAX-arena_size || o>UINTPTR_MAX-owner_size ||
        (a<o+owner_size && o<a+arena_size) || !op || !op->lock || !op->unlock ||
        !op->allocate || !op->release || !op->overlap || length>UINTPTR_MAX-start)
        return BB593_INVALID;
    if (op->lock(op->ctx)) return BB593_LOCK;
    int rc=BB593_INVALID;
    const uintptr_t limit=a+arena_size;
    const uintptr_t m=load594(owner+0x468);
    if (m<a || m>limit-0x28 || m%_Alignof(uintptr_t)) goto done;
    unsigned char *meta=arena+(m-a);
    if (load594(meta+0x20)!=o) goto done;
    const uintptr_t b=load594(meta+8), e=load594(meta+0x10), c=load594(meta+0x18);
    if (b<a || b>=c || b%_Alignof(BbArea593) || e<b || e>c || c>limit ||
        (e-b)%sizeof(BbArea593) || (c-b)%sizeof(BbArea593) || (b<m+0x28 && m<c))
        goto done;
    BbAreas593 v={(BbArea593 *)(void *)(arena+(b-a)),(e-b)/sizeof(BbArea593),
                   (c-b)/sizeof(BbArea593)};
    const BbAreaOps593 locked={op->ctx,held594,held594,op->overlap,op->allocate,op->release};
    rc=bb_registry_area_v593(&v,&locked,heap,start,length);
    if (rc==BB593_OK) {
        store594(meta+0x18,(uintptr_t)(v.base+v.capacity));
        store594(meta+0x10,(uintptr_t)(v.base+v.size));
        store594(meta+8,(uintptr_t)v.base);
    }
done:
    if (op->unlock(op->ctx)) return rc==BB593_OK?BB593_COMMITTED_UNLOCK:BB593_UNLOCK;
    return rc;
}

#ifdef BB_BIND_TEST
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
extern int candidate(unsigned char *,size_t,unsigned char *,size_t,int (*)(void *),int (*)(void *));
extern int bb_registry_cold_v592(unsigned char *,size_t,void *(*)(void *,size_t,size_t),
                                void *(*)(void *,size_t),void (*)(void *),void (*)(void *));
static _Alignas(16) unsigned char owner[0x490];
/* Allocated storage, not a declared unsigned-char array accessed as BbArea593. */
static unsigned char *arena;
static size_t cursor=0x100, releases;
static int fail, depth;
static pthread_mutex_t write_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t heap_lock=PTHREAD_MUTEX_INITIALIZER;
static int ready(void *p) { assert(p==owner+0x440); return 0; }
static int init(void *p) { assert(p==owner+0x448); return 0; }
static void take(void *p) { assert(p==owner+0x440); assert(!pthread_mutex_lock(&heap_lock)); }
static void drop(void *p) { assert(p==owner+0x440); assert(!pthread_mutex_unlock(&heap_lock)); }
static void *reserve(size_t n) {
    if (fail || n>0xff000-cursor) return NULL;
    void *p=arena+cursor; cursor+=(n+15)&~(size_t)15; return p;
}
static void *aligned(void *p,size_t n,size_t a) {
    assert(p==owner+0x458 && n==0x28 && a==8); return reserve(n);
}
static void *cold(void *p,size_t n) { assert(p==owner && n==0x300); return reserve(n); }
static int lock(void *p) {
    (void)p; if (fail==2) return 1;
    assert(!pthread_mutex_lock(&write_lock)); assert(!depth++); return 0;
}
static int unlock(void *p) {
    (void)p; assert(depth--==1); assert(!pthread_mutex_unlock(&write_lock)); return fail==3;
}
static void overlap(void *p) { (void)p; assert(depth==1); }
static BbArea593 *grow(void *p,size_t n) {
    (void)p; assert(depth==1 && n==48*sizeof(BbArea593));
    take(owner+0x440); void *r=reserve(n); drop(owner+0x440); return r;
}
static void release(void *p,BbArea593 *a) {
    (void)p; assert(depth==1 && (void *)a==arena+0x130); ++releases;
}
#include <stdlib.h>
int main(void) {
    arena=calloc(1,0x100000); assert(arena);
    assert(candidate(owner,sizeof owner,arena,0x100000,ready,init));
    assert(bb_registry_cold_v592(owner,sizeof owner,aligned,cold,take,drop)==1);
    const BbAreaOps593 op={NULL,lock,unlock,overlap,grow,release};
#define INSERT(h,s,n) bb_registry_bind_v594(owner,sizeof owner,arena,0x100000,&op,h,s,n)
    unsigned char *m=arena+0x100, before[0x28];
    assert(load594(owner+0x468)==(uintptr_t)m);
    for (unsigned i=32;i;--i) assert(INSERT(i,i*16,16)==BB593_OK);
    memcpy(before,m,sizeof before);
    assert(INSERT(16,16*16,16)==BB593_DUP);
    fail=1; assert(INSERT(33,0,16)==BB593_ALLOC);
    fail=2; assert(INSERT(33,0,16)==BB593_LOCK);
    assert(!memcmp(before,m,sizeof before) && !releases);
    fail=0; assert(INSERT(33,0,16)==BB593_OK && releases==1);
    BbArea593 *b=(BbArea593 *)load594(m+8);
    assert(load594(m+0x10)==(uintptr_t)(b+33) && load594(m+0x18)==(uintptr_t)(b+48));
    assert(b[0].heap==33);
    for (unsigned i=1;i<=32;++i) assert(b[i].heap==i && b[i].start==i*16);
    fail=3; assert(INSERT(34,33*16,16)==BB593_COMMITTED_UNLOCK && b[33].heap==34);
    fail=0;
    store594(m+0x10,(uintptr_t)b+1);
    assert(INSERT(35,0,16)==BB593_INVALID);
    store594(owner+0x468,(uintptr_t)arena+0x100000-1);
    assert(INSERT(35,0,16)==BB593_INVALID && !depth);
    free(arena);
    puts("V591 -> V592 -> V594/V593: OK");
}
#endif
