/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "heap_registry_boot_v664.h"
#include "heap_range_v665.h"
#include "heap_view_query_v667.h"
#include "provider_publish_v658.h"
#include <stddef.h>
#include "locked_heap_v663.h"
#include "regular_heap_free_v662.h"
#include <assert.h>
#include <stdio.h>

struct fixture {
    struct bb_locked_heap_v663 lock;
    unsigned calls, fail_at;
};
static void *allocate(void *ctx, size_t n, size_t a) {
    struct fixture *f=ctx;
    if (++f->calls==f->fail_at) return NULL;
    return bb_locked_heap_allocate_v663(&f->lock,n,a);
}
static int release(void *ctx, void *p) {
    struct fixture *f=ctx;
    return bb_locked_heap_free_v663(&f->lock,p);
}
static int range_enter(void *ctx) { return !pthread_mutex_lock(ctx); }
static void range_leave(void *ctx) { assert(!pthread_mutex_unlock(ctx)); }

/* A scoped native table for the tested slot, not a full game vtable. */
struct fixture_view_table {
    uintptr_t reserved[4];
    uint32_t *(*flags)(uint32_t *, const void *, uint32_t);
};
_Static_assert(offsetof(struct fixture_view_table,flags)==0x20,"query slot");
static const struct fixture_view_table view_table={.flags=bb_heap_view_flags_v667};
static uintptr_t get_dependency(void *ctx) {
    const uintptr_t owner=(uintptr_t)ctx;
    return bb_load_v661(owner+0x468) ? owner+BB_DEPENDENCY_VIEW_V659 : 0;
}
static int query(void *ctx, uintptr_t dependency, uint32_t *flags) {
    if (dependency!=(uintptr_t)ctx+BB_DEPENDENCY_VIEW_V659 ||
        bb_load_v661(dependency+8)!=(uintptr_t)ctx ||
        bb_load_v661(dependency)!=(uintptr_t)&view_table) return 0;
    const struct fixture_view_table *table=(const void *)bb_load_v661(dependency);
    return table->flags(flags,(const void *)dependency,0)==flags;
}

int main(void) {
    static _Alignas(16) unsigned char heap[BB_DEPENDENCY_BYTES_V659];
    static _Alignas(16) unsigned char backing[BB_HEAP_BACKING_V660];
    memset(backing,0xa5,sizeof backing);
    assert(bb_dependency_seed_v659(heap,sizeof heap,(struct bb_dependency_tables_v659){1,(uintptr_t)&view_table,3}));
    assert(bb_heap_seed_v660(heap,sizeof heap,backing,sizeof backing));
    struct fixture f={.lock={.heap=heap,.allocate=bb_heap_allocate_v661,.release=bb_heap_free_v662}};
    assert(bb_locked_heap_init_v663(&f.lock));
    const struct bb_boot_registry_ops_v664 ops={&f,allocate,release};
    const uintptr_t h=(uintptr_t)heap, capacity=bb_load_v661(h+24);
    unsigned char before[sizeof heap];
    memcpy(before,heap,sizeof heap);
    for (unsigned failure=1;failure<=2;++failure) {
        f.calls=0; f.fail_at=failure;
        assert(!bb_boot_registry_v664(heap,sizeof heap,&ops));
        assert(f.calls==failure && !memcmp(heap,before,sizeof heap));
    }
    _Alignas(8) unsigned char object[0x50], untouched[sizeof object];
    memset(object,0x5a,sizeof object);
    memcpy(untouched,object,sizeof object);
    struct bb_provider_cache_v658 cell={0};
    const struct bb_provider_calls_v658 calls={heap,get_dependency,query};
    assert(!bb_provider_publish_v658(&cell,object,sizeof object,1,&calls));
    assert(!cell.published && !memcmp(untouched,object,sizeof object));
    memset(backing,0xa5,sizeof backing);
    assert(bb_heap_seed_v660(heap,sizeof heap,backing,sizeof backing));
    f.calls=0; f.fail_at=0;
    assert(bb_boot_registry_v664(heap,sizeof heap,&ops)==1);
    const uintptr_t p=bb_load_v661(h+0x468), start=bb_load_v661(p+8);
    assert(f.calls==2 && p==bb_load_v661(h+8) && start==p+48);
    assert(bb_load_v661(p+16)==start && bb_load_v661(p+24)==start+0x300);
    assert(bb_load_v661(p+32)==h && bb_load_v661(h+32)==2);
    assert(bb_load_v661(h+24)==capacity-48-784);
    assert(bb_load_v661(start-8)==(start+768+3));
    uint32_t granularity;
    memcpy(&granularity,heap+0x488,4);
    assert(granularity==0x1000 && !bb_boot_registry_v664(heap,sizeof heap,&ops) && f.calls==2);
    /* Use the actual V664 registry, not a second header or stand-in buffer. */
    pthread_mutex_t range_lock=PTHREAD_MUTEX_INITIALIZER;
    const struct bb_heap_range_lock_v665 lock={&range_lock,range_enter,range_leave};
    assert(bb_heap_range_insert_v665((unsigned char *)p,lock,h,
                                     (uintptr_t)backing,sizeof backing));
    assert(bb_load_v661(start)==h && bb_load_v661(start+8)==(uintptr_t)backing);
    assert(bb_load_v661(start+16)==(uintptr_t)backing+sizeof backing);
    assert(bb_load_v661(p+16)==start+24 && bb_load_v661(p+24)==start+768);
    assert(f.calls==2 && bb_load_v661(h+32)==2);
    assert(bb_provider_publish_v658(&cell,object,sizeof object,1,&calls)==(uintptr_t)object);
    assert(bb_load_v661((uintptr_t)object+0x38)==h+BB_DEPENDENCY_VIEW_V659);
    assert(bb_load_v661((uintptr_t)object+0x18)==bb_load_v661((uintptr_t)untouched+0x18));
    assert(bb_provider_publish_v658(&cell,NULL,0,0,NULL)==(uintptr_t)object);
    /* End the fixture lifetime before tearing down the backing registry. */
    cell.published=0;
    assert(!pthread_mutex_destroy(&range_lock));
    assert(release(&f,(void *)start) && release(&f,(void *)p));
    assert(bb_load_v661(h+24)==capacity && !bb_load_v661(h+32));
    assert(!pthread_mutex_destroy(&f.lock.mutex));
    puts("V667: cold registry and real heap view connected to V658 publication");
}
