/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "singleton_direct_v526.h"
#include "native_direct_memory_host_v411.h"

static unsigned attempts;
static void *reject_map(void *ctx,uint64_t off,uint64_t len,uint64_t align,
        int type,unsigned prot) {
    (void)ctx;
    if (off==0 && len==UINT64_C(0x7400000) && align==UINT64_C(0x200000) &&
        type==0 && prot==3) ++attempts;
    return NULL;
}

int main(void) {
    const uint64_t bytes=UINT64_C(0x7400000), align=UINT64_C(0x200000);
    ShytDmPool pool={0};
    const ShytDmBackend reject={NULL,reject_map,shyt_dm_cpu_unmap};
    const ShytDmBackend real={NULL,shyt_dm_cpu_map,shyt_dm_cpu_unmap};
    struct bb_singleton_memory_v526 result={1,NULL};
    if (!shyt_dm_init(&pool,bytes+align)) return 1;
    if (bb_singleton_memory_v526(&pool,&reject,bytes,1,&result)!=BB_DM526_INVALID ||
        attempts || pool.count || result.offset!=1 || result.storage) return 2;
    if (bb_singleton_memory_v526(&pool,&reject,bytes+2*align,align,&result)!=BB_DM526_ALLOC_FAILED ||
        attempts || pool.count || result.offset!=1 || result.storage) return 3;
    if (bb_singleton_memory_v526(&pool,&reject,bytes,align,&result)!=BB_DM526_MAP_FAILED ||
        attempts!=1 || pool.count || result.offset!=1 || result.storage) return 4;
    if (bb_singleton_memory_v526(&pool,&real,bytes,align,&result)!=BB_DM526_READY ||
        pool.count!=1 || result.offset || !result.storage ||
        (uintptr_t)result.storage%align) return 5;
    unsigned char *p=result.storage;
    if (p[0] || p[bytes-1]) return 6;
    p[0]=7; p[bytes-1]=9;
    if (p[0]!=7 || p[bytes-1]!=9) return 7;
    if (shyt_dm_release(&pool,result.offset,bytes)!=SHYT_DM_OK || pool.count) return 8;
    uint64_t reserved=UINT64_MAX;
    if (shyt_dm_allocate(&pool,0,(int64_t)pool.limit,SHYT_DM_PAGE,0,0,&reserved)!=SHYT_DM_OK ||
        reserved || bb_singleton_memory_v526(&pool,&real,bytes,align,&result)!=BB_DM526_READY ||
        result.offset!=align || pool.count!=2) return 9;
    if (shyt_dm_release(&pool,result.offset,bytes)!=SHYT_DM_OK ||
        shyt_dm_release(&pool,reserved,SHYT_DM_PAGE)!=SHYT_DM_OK || pool.count) return 10;
    return 0;
}
