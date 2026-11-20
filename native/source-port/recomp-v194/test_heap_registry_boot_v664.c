/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "heap_registry_boot_v664.h"
#include "heap_range_v665.h"
#include "heap_site_v668.h"
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
static const char heap_source[]="DLHeapManager.cpp";
static int range_enter(void *ctx) {
    assert(bb_heap_site_v668.file==heap_source && bb_heap_site_v668.line==251);
    return !pthread_rwlock_wrlock(ctx);
}
static void range_leave(void *ctx) { assert(!pthread_rwlock_unlock(ctx)); }

/* A scoped native table for the tested slot, not a full game vtable. */
struct fixture_view_table {
    uintptr_t reserved[4];
    uint32_t *(*flags)(uint32_t *, const void *, uint32_t);
};
_Static_assert(offsetof(struct fixture_view_table,flags)==0x20,"query slot");
static const struct fixture_view_table view_table={.flags=bb_heap_view_flags_v667};
struct fixture_dependency {
    uintptr_t owner, begin, end;
};
static uintptr_t get_dependency(void *ctx) {
    /* This fixture is single-threaded through publication. Require the
     * actual first registry entry, not just an allocated registry header. */
    const struct fixture_dependency *d=ctx;
    const uintptr_t header=bb_load_v661(d->owner+0x468);
    const uintptr_t view=d->owner+BB_DEPENDENCY_VIEW_V659;
    if (!header || bb_load_v661(header+32)!=d->owner) return 0;
    const uintptr_t first=bb_load_v661(header+8);
    if (!first || bb_load_v661(header+16)!=first+sizeof(struct bb_heap_range_v665) ||
        bb_load_v661(first)!=view || bb_load_v661(first+8)!=d->begin ||
        bb_load_v661(first+16)!=d->end) return 0;
    return view;
}
static int query(void *ctx, uintptr_t dependency, uint32_t *flags) {
    const struct fixture_dependency *d=ctx;
    if (dependency!=d->owner+BB_DEPENDENCY_VIEW_V659 ||
        bb_load_v661(dependency+8)!=d->owner ||
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
    struct fixture_dependency dependency={h,(uintptr_t)backing,(uintptr_t)backing+sizeof backing};
    const struct bb_provider_calls_v658 calls={&dependency,get_dependency,query};
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
    assert(!bb_provider_publish_v658(&cell,object,sizeof object,1,&calls));
    assert(!cell.published && !memcmp(untouched,object,sizeof object));
    pthread_rwlock_t range_lock;
    assert(!pthread_rwlock_init(&range_lock,NULL));
    const struct bb_heap_range_lock_v665 lock={&range_lock,range_enter,range_leave};
    bb_heap_site_note_v668(heap_source,251);
    /* Retail passes its embedded interface, not the heap base, as row owner. */
    const uintptr_t view=h+BB_DEPENDENCY_VIEW_V659;
    assert(bb_heap_range_insert_v665((unsigned char *)p,lock,view,
                                     (uintptr_t)backing,sizeof backing));
    assert(bb_load_v661(start)==view && bb_load_v661(start+8)==(uintptr_t)backing);
    assert(bb_load_v661(start+16)==(uintptr_t)backing+sizeof backing);
    assert(bb_load_v661(p+16)==start+24 && bb_load_v661(p+24)==start+768);
    assert(f.calls==2 && bb_load_v661(h+32)==2);
    assert(bb_provider_publish_v658(&cell,object,sizeof object,1,&calls)==(uintptr_t)object);
    assert(bb_load_v661((uintptr_t)object+0x38)==h+BB_DEPENDENCY_VIEW_V659);
    assert(bb_load_v661((uintptr_t)object+0x18)==bb_load_v661((uintptr_t)untouched+0x18));
    assert(bb_provider_publish_v658(&cell,NULL,0,0,NULL)==(uintptr_t)object);
    /* End the fixture lifetime before tearing down the backing registry. */
    cell.published=0;
    assert(!pthread_rwlock_destroy(&range_lock));
    assert(release(&f,(void *)start) && release(&f,(void *)p));
    assert(bb_load_v661(h+24)==capacity && !bb_load_v661(h+32));
    assert(!pthread_mutex_destroy(&f.lock.mutex));
    puts("V669: cold registry stores the interface owner under a write lock before publication");
}
