/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_MEMBER_INSERT_V609_H
#define BB_MEMBER_INSERT_V609_H
#include "class_table_v554.h"

/* Table mutation only; member creation, reuse lookup and handler append
 * remain the caller's responsibility. The 40-byte view starts at +0x18
 * of a class descriptor; its first eight bytes are not modified. */
static inline enum bb_class_v554 bb_member_insert_v609(unsigned char *h,size_t n,uint64_t hva,
        const struct bb_vector_block_v541 *old,uint64_t member,const char *name,
        uint64_t wide,void *ctx,
        int (*alloc)(void *,uint64_t,size_t,struct bb_vector_block_v541 *),
        int (*release)(void *,uint64_t,uint64_t)) {
    if (!name) return BB_CLASS_INVALID;
    const uint64_t row[4]={member,(uintptr_t)name,wide,strlen(name)};
    return bb_class_insert_floor_v609(h,n,hva,old,row,0x80,ctx,alloc,release);
}
#endif
