/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "member_lookup_v608.c"
#include "member_insert_v609.h"
#include "member_object_v611.h"

typedef struct {
    void *ctx,*object_allocator;
    uintptr_t lock_table;
    BbHandlerOps610 heap;
    int (*init_lock)(void *,uintptr_t *);
    void (*destroy_lock)(void *,uintptr_t);
} BbMemberHost612;

/* Serialized startup only. descriptor is live 0x40-byte writable storage;
 * all ancestor row ranges are live. On post-publication error stop startup:
 * the already published member remains owned by the class. */
static int vector_alloc612(void *v,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    const BbMemberHost612 *h=v;
    void *p=h->heap.allocate((void *)(uintptr_t)owner,n,8);
    if (!p) return 0;
    *out=(struct bb_vector_block_v541){p,n,(uintptr_t)p};
    return 1;
}
static int vector_free612(void *v,uint64_t owner,uint64_t p) {
    const BbMemberHost612 *h=v;
    h->heap.release((void *)(uintptr_t)owner,(uintptr_t *)(uintptr_t)p);
    return 1;
}
int bb_member_register_v612(void *descriptor,const char *name,const uint16_t *wide,
        uintptr_t callback,const BbMemberHost612 *h) {
    if (!descriptor || !name || !callback || !h || !h->heap.allocate || !h->heap.release)
        return -1;
    void *found;
    int lookup=bb_member_lookup_v608(descriptor,name,256,&found);
    if (lookup<0) return -1;
    if (!lookup) {
        if (!h->object_allocator || !h->lock_table || !h->init_lock || !h->destroy_lock)
            return -1;
        unsigned char *v=(unsigned char *)descriptor+0x18;
        uint64_t b=bb_vector_word_v541(v+8),e=bb_vector_word_v541(v+16);
        uint64_t l=bb_vector_word_v541(v+24),owner=bb_vector_word_v541(v+32);
        if (!owner || ((b|e|l)&7) || b>e || e>l || (!b && l) ||
            ((e-b)|(l-b))%32) return -1;
        if (b==e && l-b<0x80) {
            struct bb_vector_block_v541 fresh;
            if (!vector_alloc612((void *)h,owner,0x80,&fresh)) return 0;
            if (b) vector_free612((void *)h,owner,b);
            b=e=fresh.va; l=b+0x80;
            bb_arena_store_v527(v+8,b);
            bb_arena_store_v527(v+16,e);
            bb_arena_store_v527(v+24,l);
        }
        BbMemberObject611 *m=(void *)h->heap.allocate(h->object_allocator,sizeof *m,8);
        if (!m) return 0;
        if (bb_member_init_v611(m,descriptor,name,wide,h->object_allocator,h->lock_table,
                h->init_lock,h->ctx)!=1) {
            h->heap.release(h->object_allocator,(void *)m);
            return 0;
        }
        const struct bb_vector_block_v541 old={(unsigned char *)(uintptr_t)b,l-b,b};
        if (bb_member_insert_v609(v,40,(uintptr_t)v,&old,(uintptr_t)m,name,(uintptr_t)wide,
                (void *)h,vector_alloc612,vector_free612)!=BB_CLASS_OK) {
            h->destroy_lock(h->ctx,m->lock_handle);
            h->heap.release(h->object_allocator,(void *)m);
            return 0;
        }
        found=m;
    }
    BbMemberObject611 *m=found;
    return bb_handler_append_v610(&m->handlers,callback,&h->heap)==1?1:-2;
}
