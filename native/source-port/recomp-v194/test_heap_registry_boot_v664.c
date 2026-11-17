/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "heap_registry_boot_v664.h"
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
int main(void) {
    static _Alignas(16) unsigned char heap[BB_DEPENDENCY_BYTES_V659];
    static _Alignas(16) unsigned char backing[BB_HEAP_BACKING_V660];
    memset(backing,0xa5,sizeof backing);
    assert(bb_dependency_seed_v659(heap,sizeof heap,(struct bb_dependency_tables_v659){1,2,3}));
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
    assert(release(&f,(void *)start) && release(&f,(void *)p));
    assert(bb_load_v661(h+24)==capacity && !bb_load_v661(h+32));
    assert(!pthread_mutex_destroy(&f.lock.mutex));
    puts("V664: cold 32-record registry, both allocation failures, no duplicate publication");
}
