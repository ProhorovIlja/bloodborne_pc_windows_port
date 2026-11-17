/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "member_object_v611.h"
#include <assert.h>
#include <pthread.h>

static int recursive(void *ctx,uintptr_t *handle) {
    pthread_mutexattr_t attr;
    if (pthread_mutexattr_init(&attr)) return -1;
    int rc=pthread_mutexattr_settype(&attr,PTHREAD_MUTEX_RECURSIVE);
    if (!rc) rc=pthread_mutex_init(ctx,&attr);
    pthread_mutexattr_destroy(&attr);
    if (!rc) *handle=(uintptr_t)ctx;
    return rc;
}
static int fail(void *ctx,uintptr_t *h) { (void)ctx; (void)h; return -1; }
int main(void) {
    BbMemberObject611 m;
    pthread_mutex_t lock;
    memset(&m,0xa5,sizeof m);
    assert(bb_member_init_v611(&m,&m,"test",NULL,&lock,1,fail,NULL)==0);
    assert(!m.lock_ready && !m.handlers.begin && !m.auxiliary.begin);
    assert(bb_member_init_v611(&m,&m,"test",NULL,&lock,1,recursive,&lock)==1);
    assert(m.lock_ready && m.lock_handle==(uintptr_t)&lock);
    assert(m.opaque18==UINT64_C(0xa5a5a5a5a5a5a5a5) && m.opaque40==m.opaque18);
    assert(!pthread_mutex_lock(&lock));
    assert(!pthread_mutex_lock(&lock));
    assert(!pthread_mutex_unlock(&lock));
    assert(!pthread_mutex_unlock(&lock));
    assert(!pthread_mutex_destroy(&lock));
    return 0;
}
