/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_SINGLETON_CTOR_V576_H
#define BB_SINGLETON_CTOR_V576_H
#include "mutex_gate_v574.h"
#include <string.h>

struct bb_singleton_v576 {
    struct bb_mutex_gate_v574 gate;
    size_t published, storage, extent, guard;
};
struct bb_singleton_calls_v576 {
    struct bb_mutex_calls_v574 gate;
    int (*lock)(void *, unsigned char *, int32_t);
    int (*unlock)(void *, unsigned char *);
    int (*construct)(void *, unsigned char *, size_t);
};
enum bb_singleton_result_v576 { BB_SINGLETON_INVALID, BB_SINGLETON_OK, BB_SINGLETON_STOP };

/* Translated startup only. The caller owns all state and must discard it
 * on STOP. Host lock or construction failure never publishes a new object.
 * The publication is a native pointer; serialized input uses a zero slot. */
static inline enum bb_singleton_result_v576 bb_singleton_ctor_v576(
    unsigned char *data,size_t n,struct bb_singleton_v576 x,
    const struct bb_singleton_calls_v576 *f,void *ctx) {
    const size_t at[]={x.gate.object,x.gate.ready,x.gate.guard,x.published,x.storage,x.guard};
    const size_t len[]={17,1,1,8,x.extent,1};
    if (!data || sizeof(uintptr_t)!=8 || !x.gate.table || !f || !f->lock || !f->unlock ||
        !f->construct || !f->gate.acquire || !f->gate.release || !f->gate.probe || !f->gate.init ||
        ((x.gate.object|x.published|x.storage)&7)) return BB_SINGLETON_INVALID;
    for (size_t i=0;i<6;++i) {
        if (!len[i] || len[i]>n || at[i]>n-len[i]) return BB_SINGLETON_INVALID;
        for (size_t j=0;j<i;++j)
            if (at[i]<at[j]+len[j] && at[j]<at[i]+len[i]) return BB_SINGLETON_INVALID;
    }
    uintptr_t published=0;
    memcpy(&published,data+x.published,8);
    if (published) return BB_SINGLETON_OK;
    if (!bb_mutex_gate_v574(data,n,x.gate,&f->gate,ctx)) return BB_SINGLETON_INVALID;
    unsigned char *mutex=data+x.gate.object;
    if (!f->lock(ctx,mutex,-1)) return BB_SINGLETON_STOP;
    memcpy(&published,data+x.published,8);
    int ok=1;
    if (!published) {
        unsigned char *guard=data+x.guard;
        if (!*guard && f->gate.acquire(ctx,guard)) f->gate.release(ctx,guard);
        ok=f->construct(ctx,data+x.storage,x.extent);
        if (ok) {
            published=(uintptr_t)(data+x.storage);
            memcpy(data+x.published,&published,8);
        }
    }
    return f->unlock(ctx,mutex) && ok ? BB_SINGLETON_OK : BB_SINGLETON_STOP;
}
#endif
