/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Native publication wrapper for the factory at retail RVA 0x207bbf0.
 * Reuses the V595 cold path; compile instead of the V595 unity unit. */
#include "registry_factory_v595.c"

typedef struct { void *published; int terminal; } BbRegistryOnce596;
typedef struct {
    void *ctx;
    int (*lock)(void *), (*unlock)(void *), (*rw_init)(void *,void *);
    uintptr_t mutex_table, allocator_table, rw_table;
} BbRegistryHost596;

/* The state and callbacks must stay live for the owner's lifetime. All
 * callers use the same gate, owner and arena. Callbacks may not reenter.
 * A failed gate unlock is fatal for the caller, including on warm reads. */
void *bb_registry_once_v596(BbRegistryOnce596 *s,const BbRegistryHost596 *h,
    unsigned char *owner,size_t os,unsigned char *arena,size_t as,
    int (*ready)(void *),int (*init)(void *),void *(*aligned)(void *,size_t,size_t),
    void *(*allocate)(void *,size_t),void (*take)(void *),void (*drop)(void *),
    const BbAreaOps593 *area,void (*context)(void *,const void *,uint32_t),
    const void *source,int *status) {
    if (!status) return NULL;
    *status=BB593_INVALID;
    if (sizeof(uintptr_t)!=8 || !s || !h || !h->lock || !h->unlock || !h->rw_init ||
        !h->mutex_table || !h->allocator_table || !h->rw_table || !owner || os<0x48c ||
        ((uintptr_t)owner&7) || !arena || as!=0x100000 || !ready || !init || !aligned ||
        !allocate || !take || !drop || !area || !area->lock || !area->unlock ||
        !area->overlap || !area->allocate || !area->release || !context || !source) return NULL;
    const uintptr_t o=(uintptr_t)owner,a=(uintptr_t)arena;
    if (o>UINTPTR_MAX-os || a>UINTPTR_MAX-as || (o<a+as && a<o+os)) return NULL;
    if (h->lock(h->ctx)) { *status=BB593_LOCK; return NULL; }
    if (s->published) {
        *status=s->published==owner?BB593_OK:BB593_INVALID;
    } else if (s->terminal) {
        *status=s->terminal;
    } else {
        memset(owner,0,0x440);
        store594(owner+0x440,h->mutex_table);
        owner[0x450]=0;
        store594(owner+0x458,h->allocator_table);
        store594(owner+0x460,o);
        store594(owner+0x468,0);
        store594(owner+0x470,h->rw_table);
        owner[0x480]=0;
        if (h->rw_init(h->ctx,owner+0x470)) {
            s->terminal=*status=BB593_LOCK;
        } else {
            memset(owner+0x488,0,4);
            /* Unlike retail, do not publish before cold work finishes. */
            if (bb_registry_factory_cold_v595(owner,os,arena,as,ready,init,
                aligned,allocate,take,drop,area,context,source,status)) {
                s->published=owner;
                *status=BB593_OK;
            } else s->terminal=*status;
        }
    }
    void *result=*status==BB593_OK?s->published:NULL;
    if (h->unlock(h->ctx)) {
        *status=result?BB593_COMMITTED_UNLOCK:BB593_UNLOCK;
        return NULL;
    }
    return result;
}
