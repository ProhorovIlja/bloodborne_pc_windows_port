/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_MUTEX_HOST_V523_H
#define BB_MUTEX_HOST_V523_H
#include <errno.h>
#include <pthread.h>
#include "mutex_init_v522.h"

/* One caller-owned slot. Initialization/destruction is serialized externally.
 * The guest address is an opaque key, not a host pointer or an ABI layout. */
struct bb_mutex_slot_v523 { pthread_mutex_t mutex; uint64_t key; };
struct bb_mutex_session_v523 {
    struct bb_mutex_slot_v523 *slot;
    pthread_mutexattr_t attr;
    int live, failed;
};

static inline int bb_mutex_hook_v523(void *ctx, enum bb_mutex_op_v522 op,
        uint64_t object, uint64_t *token, uint32_t type, uint32_t *rc) {
    struct bb_mutex_session_v523 *s=ctx;
    *rc=0;
    if (op==BB_ATTR_INIT_V522) {
        s->failed=pthread_mutexattr_init(&s->attr);
        s->live=!s->failed;
        *token=(uint64_t)s->live;
    } else if (op==BB_ATTR_TYPE_V522 && s->live && *token==1 && type==2) {
        s->failed=pthread_mutexattr_settype(&s->attr,PTHREAD_MUTEX_RECURSIVE);
    } else if (op==BB_MUTEX_INIT_V522 && s->live && *token==1 && !s->failed && object && !s->slot->key) {
        const int err=pthread_mutex_init(&s->slot->mutex,&s->attr);
        switch (err) {
        case 0: s->slot->key=object; break;
        case ENOMEM: *rc=UINT32_C(0x8002000c); break;
        case EAGAIN: *rc=UINT32_C(0x80020023); break;
        case EINVAL: *rc=UINT32_C(0x80020016); break;
        default: return 0;
        }
    } else if (op==BB_ATTR_DESTROY_V522 && s->live && *token==1) {
        const int err=pthread_mutexattr_destroy(&s->attr);
        s->live=0; *token=0;
        return !err;
    } else return 0;
    return !s->failed;
}

static inline struct bb_mutex_result_v522 bb_mutex_host_v523(
        struct bb_mutex_slot_v523 *slot, uint64_t object) {
    if (!slot || slot->key || !object)
        return (struct bb_mutex_result_v522){BB_MUTEX_MISS_V522,0,0};
    struct bb_mutex_session_v523 s={.slot=slot};
    struct bb_mutex_result_v522 r=bb_mutex_init_v522(object,bb_mutex_hook_v523,&s);
    if (s.live) (void)pthread_mutexattr_destroy(&s.attr);
    return r;
}
#endif
