/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "heap_site_v668.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>

struct job { const char *file; uint32_t line; };
static pthread_barrier_t barrier;
static void sync_workers(void) {
    const int rc=pthread_barrier_wait(&barrier);
    assert(!rc || rc==PTHREAD_BARRIER_SERIAL_THREAD);
}
static void *worker(void *arg) {
    const struct job *j=arg;
    assert(!bb_heap_site_v668.file && !bb_heap_site_v668.line && !bb_heap_site_v668.other);
    bb_heap_site_v668.untouched=j->line+1;
    bb_heap_site_v668.other=j->line+2;
    for (unsigned i=0;i<256;++i) {
        bb_heap_site_note_v668(j->file,j->line+i);
        sync_workers();
        assert(bb_heap_site_v668.file==j->file && bb_heap_site_v668.line==j->line+i);
        assert(bb_heap_site_v668.untouched==j->line+1 && bb_heap_site_v668.other==j->line+2);
        sync_workers();
    }
    return NULL;
}
int main(void) {
    struct job a={"one",251}, b={"two",17};
    pthread_t x,y;
    bb_heap_site_note_v668("main",2);
    assert(!pthread_barrier_init(&barrier,NULL,2));
    assert(!pthread_create(&x,NULL,worker,&a) && !pthread_create(&y,NULL,worker,&b));
    assert(!pthread_join(x,NULL) && !pthread_join(y,NULL));
    assert(bb_heap_site_v668.line==2 && !bb_heap_site_v668.other);
    assert(!pthread_barrier_destroy(&barrier));
    puts("V668: independent per-thread heap-site state, adjacent fields preserved");
}
