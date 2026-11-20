/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_LOCKED_HEAP_V663_H
#define BB_LOCKED_HEAP_V663_H
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>

/* Host-side primary lock only; do not copy or move it after initialization.
 * The caller owns activation/publication and must quiesce before teardown. */
struct bb_locked_heap_v663 {
    pthread_mutex_t mutex;
    unsigned char *heap;
    void *(*allocate)(unsigned char *, uintptr_t, uintptr_t);
    int (*release)(unsigned char *, void *);
};
static inline int bb_locked_heap_init_v663(struct bb_locked_heap_v663 *s) {
    if (!s || !s->heap || !s->allocate || !s->release) return 0;
    pthread_mutexattr_t attr;
    if (pthread_mutexattr_init(&attr)) return 0;
    int rc=pthread_mutexattr_settype(&attr,PTHREAD_MUTEX_RECURSIVE);
    if (!rc) rc=pthread_mutex_init(&s->mutex,&attr);
    pthread_mutexattr_destroy(&attr);
    return rc==0;
}
static inline void bb_locked_heap_unlock_v663(struct bb_locked_heap_v663 *s) {
    if (pthread_mutex_unlock(&s->mutex)) abort();
}
static inline void *bb_locked_heap_allocate_v663(struct bb_locked_heap_v663 *s,
                                                uintptr_t size, uintptr_t alignment) {
    if (pthread_mutex_lock(&s->mutex)) return NULL;
    void *p=s->allocate(s->heap,size,alignment);
    bb_locked_heap_unlock_v663(s);
    return p;
}
static inline int bb_locked_heap_free_v663(struct bb_locked_heap_v663 *s, void *p) {
    if (pthread_mutex_lock(&s->mutex)) return 0;
    int ok=s->release(s->heap,p);
    bb_locked_heap_unlock_v663(s);
    return ok;
}
#endif
