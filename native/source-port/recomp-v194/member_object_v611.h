/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_MEMBER_OBJECT_V611_H
#define BB_MEMBER_OBJECT_V611_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "member_handlers_v610.h"

typedef struct {
    void *owner;
    const char *name;
    const uint16_t *wide;
    uint64_t opaque18;
    BbHandlerVector610 handlers;
    uint64_t opaque40;
    BbHandlerVector610 auxiliary;
    uint64_t zero68;
    uintptr_t lock_table, lock_handle;
    unsigned char lock_ready, opaque81[7];
} BbMemberObject611;
_Static_assert(sizeof(BbMemberObject611)==0x88 &&
    offsetof(BbMemberObject611,handlers)==0x20 &&
    offsetof(BbMemberObject611,auxiliary)==0x48 &&
    offsetof(BbMemberObject611,lock_handle)==0x78 &&
    offsetof(BbMemberObject611,lock_ready)==0x80, "member object ABI");

/* Caller owns unpublished aligned storage and the lifetimes of all inputs.
 * init supplies a recursive host lock handle. Never publish on failure. */
static inline int bb_member_init_v611(BbMemberObject611 *m,void *owner,
    const char *name,const uint16_t *wide,void *allocator,uintptr_t table,
    int (*init)(void *,uintptr_t *),void *ctx) {
    if (!m || !owner || !name || !allocator || !table || !init) return -1;
    m->owner=owner; m->name=name; m->wide=wide;
    m->handlers=(BbHandlerVector610){.allocator=allocator};
    m->auxiliary=(BbHandlerVector610){.allocator=allocator};
    m->zero68=0;
    m->lock_table=table;
    m->lock_ready=0;
    if (init(ctx,&m->lock_handle)) return 0;
    m->lock_ready=1;
    return 1;
}
#endif
