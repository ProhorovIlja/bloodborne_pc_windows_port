/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "heap_range_v665.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>

struct guard { pthread_mutex_t mutex; unsigned enters, leaves; int reject; };
static int enter(void *p) {
    struct guard *g=p;
    if (g->reject || pthread_mutex_lock(&g->mutex)) return 0;
    ++g->enters;
    return 1;
}
static void leave(void *p) {
    struct guard *g=p;
    ++g->leaves;
    assert(!pthread_mutex_unlock(&g->mutex));
}
int main(void) {
    struct guard g={.mutex=PTHREAD_MUTEX_INITIALIZER};
    const struct bb_heap_range_lock_v665 lock={&g,enter,leave};
    unsigned char header[40]={0};
    struct bb_heap_range_v665 rows[4]={0}, snapshot[4];
    uintptr_t first=(uintptr_t)rows, limit=first+sizeof rows;
    memcpy(header+8,&first,8);
    memcpy(header+16,&first,8);
    memcpy(header+24,&limit,8);
    assert(bb_heap_range_insert_v665(header,lock,1,0x200000,0x100000));
    assert(bb_heap_range_insert_v665(header,lock,2,0x100000,0x100000));
    assert(bb_heap_range_insert_v665(header,lock,3,0x400000,0x100000));
    memcpy(snapshot,rows,sizeof rows);
    assert(!bb_heap_range_insert_v665(header,lock,5,0x280000,0x100000));
    assert(!bb_heap_range_insert_v665(header,lock,1,0x600000,8));
    assert(!bb_heap_range_insert_v665(header,lock,5,UINTPTR_MAX,8));
    g.reject=1;
    assert(!bb_heap_range_insert_v665(header,lock,5,0x600000,8));
    g.reject=0;
    assert(!memcmp(snapshot,rows,sizeof rows));
    assert(bb_heap_range_insert_v665(header,lock,4,0x300000,0x100000));
    assert(!bb_heap_range_insert_v665(header,lock,5,0x600000,8));
    for (unsigned i=0;i<4;++i) {
        assert(rows[i].begin==(i+1)*0x100000);
        assert(rows[i].end==(i+2)*0x100000);
    }
    uintptr_t last;
    memcpy(&last,header+16,8);
    assert(last==limit && g.enters==7 && g.leaves==7);
    assert(!pthread_mutex_destroy(&g.mutex));
    puts("V665: 1 MiB registration, insertion order, rejection and lock balance passed");
}
