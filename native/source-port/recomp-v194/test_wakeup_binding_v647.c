/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "wakeup_binding_v647.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>

struct state { pthread_mutex_t lock; unsigned init, acquire, release; int deny; };
static int acquire(void *ctx,unsigned char *g) { ++((struct state *)ctx)->acquire; return !*g; }
static void release(void *ctx,unsigned char *g) { ++((struct state *)ctx)->release; *g=1; }
static unsigned char probe(void *ctx,unsigned char *obj) { (void)ctx; return obj[16]; }
static int init(void *ctx,unsigned char *slot) {
    struct state *s=ctx;
    (void)slot;
    ++s->init;
    if (s->deny) return 1;
    pthread_mutexattr_t attr;
    assert(!pthread_mutexattr_init(&attr));
    assert(!pthread_mutexattr_settype(&attr,PTHREAD_MUTEX_RECURSIVE));
    assert(!pthread_mutex_init(&s->lock,&attr));
    assert(!pthread_mutexattr_destroy(&attr));
    return 0;
}

int main(void) {
    static const struct bb_mutex_calls_v574 calls={acquire,release,probe,init};
    for (int mode=0;mode<3;++mode) {
        unsigned char data[32]={0};
        struct state s={.deny=mode==2};
        const struct bb_mutex_gate_v574 gate={0,24,25,1};
        struct bb_wakeup_binding_v647 b={data,sizeof data,gate,&calls,&s};
        if (mode==1) assert(bb_mutex_gate_v574(data,sizeof data,gate,&calls,&s));
        unsigned char *(*get)(const struct bb_wakeup_binding_v647 *)=bb_wakeup_get_v647;
        for (int i=0;i<32;++i) assert(get(&b)==(s.deny ? NULL : data));
        assert(s.init==1 && s.acquire==1 && s.release==1 && data[24]==1 && data[25]==1);
        if (!s.deny) {
            assert(!pthread_mutex_lock(&s.lock) && !pthread_mutex_lock(&s.lock));
            assert(!pthread_mutex_unlock(&s.lock) && !pthread_mutex_unlock(&s.lock));
            assert(!pthread_mutex_destroy(&s.lock));
        }
        b.gate.guard=16;
        assert(!get(&b) && s.init==1);
    }
    assert(!bb_wakeup_get_v647(NULL));
    puts("wakeup binding: cold, shared warm, failure, invalid layout OK");
}
