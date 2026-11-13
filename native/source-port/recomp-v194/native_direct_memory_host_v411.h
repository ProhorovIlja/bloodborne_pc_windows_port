/* SPDX-License-Identifier: GPL-2.0-or-later
 * CPU-only zero-filled storage for the V411 startup subset. Not a guest
 * virtual address mapping; no execution, GPU visibility or aliases.
 */
#ifndef SHYT_NATIVE_DIRECT_MEMORY_HOST_V411_H
#define SHYT_NATIVE_DIRECT_MEMORY_HOST_V411_H
#include "native_direct_memory_v411.h"
#include <stdlib.h>

static inline void *shyt_dm_cpu_map(void *ctx,uint64_t off,uint64_t len,
    uint64_t align,int type,unsigned protection) {
    (void)ctx; (void)off; (void)type;
    if(protection!=3 || !len || align<SHYT_DM_PAGE || align>UINTPTR_MAX ||
       align>SIZE_MAX-sizeof(void *) ||
       len>SIZE_MAX-(size_t)align-sizeof(void *))return NULL;
    const size_t bytes=(size_t)len+(size_t)align+sizeof(void *);
    unsigned char *raw=calloc(1,bytes);
    if(!raw)return NULL;
    unsigned char *start=raw+sizeof(void *);
    const uintptr_t remainder=(uintptr_t)start%(uintptr_t)align;
    unsigned char *result=start+(remainder?(uintptr_t)align-remainder:0);
    void *owner=raw;
    memcpy(result-sizeof owner,&owner,sizeof owner);
    return result;
}
static inline int shyt_dm_cpu_unmap(void *ctx,void *ptr,uint64_t len) {
    (void)ctx; (void)len;
    void *owner=NULL;
    memcpy(&owner,(unsigned char *)ptr-sizeof owner,sizeof owner);
    free(owner);
    return 1;
}
#endif
