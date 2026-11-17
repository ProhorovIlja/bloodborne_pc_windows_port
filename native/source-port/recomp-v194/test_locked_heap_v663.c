/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "locked_heap_v663.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifdef BB_V663_REPOSITORY_HEAP
#include "regular_heap_free_v662.h"
#else
static void *alloc_host(unsigned char *h, uintptr_t n, uintptr_t a) {
    (void)h;
    return a<=16 && n<=256 ? malloc(n) : NULL;
}
static int free_host(unsigned char *h, void *p) { (void)h; free(p); return 1; }
#endif
static void *worker(void *arg) {
    struct bb_locked_heap_v663 *s=arg;
    for (unsigned i=0;i<1000;++i) {
        const size_t n=40+i%217;
        unsigned char *p=bb_locked_heap_allocate_v663(s,n,8);
        assert(p && !((uintptr_t)p&7));
        memset(p,0x45,n);
        assert(p[n-1]==0x45);
        assert(bb_locked_heap_free_v663(s,p));
    }
    return NULL;
}
int main(void) {
#ifdef BB_V663_REPOSITORY_HEAP
    static _Alignas(16) unsigned char heap[BB_HEAP_HEADER_V660], backing[BB_HEAP_BACKING_V660];
    assert(bb_heap_seed_v660(heap,sizeof heap,backing,sizeof backing));
    const uintptr_t capacity=bb_load_v661((uintptr_t)heap+24);
    struct bb_locked_heap_v663 s={.heap=heap,.allocate=bb_heap_allocate_v661,.release=bb_heap_free_v662};
#else
    unsigned char heap;
    struct bb_locked_heap_v663 s={.heap=&heap,.allocate=alloc_host,.release=free_host};
#endif
    assert(!bb_locked_heap_init_v663(NULL));
    assert(bb_locked_heap_init_v663(&s));
    assert(!pthread_mutex_lock(&s.mutex));
    assert(!bb_locked_heap_allocate_v663(&s,40,32));
    void *p=bb_locked_heap_allocate_v663(&s,40,8);
    assert(p && bb_locked_heap_free_v663(&s,p));
    assert(!pthread_mutex_unlock(&s.mutex));
    pthread_t threads[4];
    for(unsigned i=0;i<4;++i) assert(!pthread_create(&threads[i],NULL,worker,&s));
    for(unsigned i=0;i<4;++i) assert(!pthread_join(threads[i],NULL));
#ifdef BB_V663_REPOSITORY_HEAP
    assert(bb_load_v661((uintptr_t)heap+24)==capacity);
    assert(!bb_load_v661((uintptr_t)heap+32));
#endif
    assert(!pthread_mutex_destroy(&s.mutex));
    puts("V663: recursive lock, failed allocation, 4000 concurrent allocate/free pairs");
}
