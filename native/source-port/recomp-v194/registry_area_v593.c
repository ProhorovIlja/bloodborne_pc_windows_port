/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Area-vector algorithm adapted from Paleblood game/engine/heap_manager_register_area.cpp
 * (GPL-2.0-or-later, blob da02429f29f75096fa70e56dc0412ceef90853c2).
 * No RT_ORIGINAL/RT_GLOBAL. This is not a DLRuntimeClass table. */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct { uintptr_t heap, start, end; } BbArea593;
typedef struct { BbArea593 *base; size_t size, capacity; } BbAreas593;
typedef struct {
    void *ctx;
    int (*lock)(void *), (*unlock)(void *);
    void (*overlap)(void *);
    BbArea593 *(*allocate)(void *,size_t);
    void (*release)(void *,BbArea593 *);
} BbAreaOps593;
enum { BB593_DUP=0, BB593_OK=1, BB593_INVALID=-1, BB593_LOCK=-2,
       BB593_ALLOC=-3, BB593_UNLOCK=-4, BB593_COMMITTED_UNLOCK=-5 };

/* Caller supplies live storage, a matched allocator/releaser, and one write
 * lock protecting the vector. allocate returns disjoint storage or NULL;
 * overlap is a non-reentrant diagnostic. An unlock failure after mutation
 * is explicitly distinguishable: callers must not replay the operation. */
int bb_registry_area_v593(BbAreas593 *v, const BbAreaOps593 *op,
                          uintptr_t heap, uintptr_t start, uintptr_t length) {
    const size_t max=SIZE_MAX/sizeof(BbArea593);
    if (!heap) return BB593_DUP;
    if (!v || !op || !op->lock || !op->unlock || !op->overlap ||
        !op->allocate || !op->release || length>UINTPTR_MAX-start)
        return BB593_INVALID;
    if (op->lock(op->ctx)) return BB593_LOCK;
    int result=BB593_INVALID;
    if (v->size>v->capacity || v->capacity>max || (!!v->base!=!!v->capacity))
        goto done;
    const BbArea593 item={heap,start,start+length};
    size_t pos=v->size;
    while (pos) {
        const BbArea593 *prev=v->base+pos-1;
        if (prev->end>start) {
            if (prev->start>start) { --pos; continue; }
            if (prev->end<item.end) op->overlap(op->ctx);
        }
        if (prev->heap==heap) { result=BB593_DUP; goto done; }
        break;
    }
    if (v->size==v->capacity) {
        size_t n=v->size, half=n/2;
        if (n==max) goto done;
        size_t cap=half>max-n?0:n+half;
        if (cap<n+1) cap=n+1;
        BbArea593 *next=op->allocate(op->ctx,cap*sizeof(*next));
        if (!next) { result=BB593_ALLOC; goto done; }
        next[pos]=item;
        if (pos) memcpy(next,v->base,pos*sizeof(*next));
        if (n>pos) memcpy(next+pos+1,v->base+pos,(n-pos)*sizeof(*next));
        if (v->base) op->release(op->ctx,v->base);
        v->capacity=cap;
        v->size=n+1;
        v->base=next;
    } else {
        if (v->size>pos) memmove(v->base+pos+1,v->base+pos,(v->size-pos)*sizeof(item));
        v->base[pos]=item;
        ++v->size;
    }
    result=BB593_OK;
done:
    if (op->unlock(op->ctx)) return result==BB593_OK?BB593_COMMITTED_UNLOCK:BB593_UNLOCK;
    return result;
}

#ifdef BB_AREA_TEST
#include <assert.h>
#include <stdio.h>
static BbArea593 old[32], next[48];
static unsigned depth, reports, allocations, releases, fail;
static int lock(void *ctx) { (void)ctx; if (fail==2) return 1; assert(!depth++); return 0; }
static int unlock(void *ctx) { (void)ctx; assert(depth--==1); return fail==3; }
static void overlap(void *ctx) { (void)ctx; assert(depth==1); ++reports; }
static BbArea593 *allocate(void *ctx,size_t bytes) {
    (void)ctx; assert(depth==1 && bytes==sizeof next); ++allocations;
    return fail==1?NULL:next;
}
static void release(void *ctx,BbArea593 *p) { (void)ctx; assert(depth==1 && p==old); ++releases; }
int main(void) {
    BbAreas593 v={old,0,32};
    const BbAreaOps593 op={NULL,lock,unlock,overlap,allocate,release};
    assert(bb_registry_area_v593(&v,&op,0,0,0)==BB593_DUP && !depth);
    assert(bb_registry_area_v593(&v,&op,1,UINTPTR_MAX,1)==BB593_INVALID);
    for (size_t i=32;i;i--)
        assert(bb_registry_area_v593(&v,&op,i,i*16,16)==BB593_OK);
    assert(v.size==32 && v.base==old && !allocations);
    assert(bb_registry_area_v593(&v,&op,16,16*16+1,16)==BB593_DUP && reports==1);
    fail=1;
    assert(bb_registry_area_v593(&v,&op,90,0,16)==BB593_ALLOC);
    assert(v.size==32 && v.capacity==32 && v.base==old && !releases);
    for (size_t i=0;i<32;++i) assert(old[i].heap==i+1 && old[i].start==(i+1)*16);
    fail=2;
    assert(bb_registry_area_v593(&v,&op,90,0,16)==BB593_LOCK && allocations==1);
    fail=0;
    assert(bb_registry_area_v593(&v,&op,90,0,16)==BB593_OK);
    assert(v.size==33 && v.capacity==48 && v.base==next && allocations==2 && releases==1);
    assert(next[0].heap==90 && memcmp(next+1,old,sizeof old)==0);
    fail=3;
    assert(bb_registry_area_v593(&v,&op,91,33*16,16)==BB593_COMMITTED_UNLOCK);
    assert(v.size==34 && !depth && next[33].heap==91);
    puts("registry area: OK");
}
#endif
