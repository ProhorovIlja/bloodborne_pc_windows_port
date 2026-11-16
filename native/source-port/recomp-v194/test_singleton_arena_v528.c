/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "singleton_arena_v528.h"
#include "native_direct_memory_host_v411.h"
#include <string.h>

static uint64_t get(const unsigned char *p) {
    uint64_t v=0;
    for (unsigned i=0;i<8;++i) v|=(uint64_t)p[i]<<(8*i);
    return v;
}
static void *reject(void *c,uint64_t o,uint64_t n,uint64_t a,int t,unsigned p) {
    (void)c;(void)o;(void)n;(void)a;(void)t;(void)p;
    return NULL;
}
int main(void) {
    const size_t bytes=UINT32_C(0x7400000), align=UINT32_C(0x200000);
    const uint64_t va=UINT64_C(0x600000000000), objva=UINT64_C(0x500000000000);
    unsigned char obj[1200], before[sizeof obj];
    memset(obj,0xa5,sizeof obj); memcpy(before,obj,sizeof obj);
    ShytDmPool pool={0};
    if (!shyt_dm_init(&pool,bytes+align)) return 1;
    struct bb_singleton_memory_v526 out={123,NULL};
    const ShytDmBackend bad={NULL,reject,shyt_dm_cpu_unmap};
    const ShytDmBackend good={NULL,shyt_dm_cpu_map,shyt_dm_cpu_unmap};
    if (bb_singleton_arena_v528(&pool,&good,obj,sizeof obj,16,24,objva,va,bytes,align,&out)!=BB_ARENA_INVALID ||
        bb_singleton_arena_v528(&pool,&good,obj,sizeof obj,16,1120,va,va,bytes,align,&out)!=BB_ARENA_INVALID ||
        bb_singleton_arena_v528(&pool,&bad,obj,sizeof obj,16,1120,objva,va,bytes,align,&out)!=BB_ARENA_MAP ||
        memcmp(obj,before,sizeof obj) || pool.count || out.offset!=123 || out.storage) return 2;
    for (unsigned i=0;i<2;++i) {
        uint64_t reserved;
        if (i && (shyt_dm_allocate(&pool,0,(int64_t)pool.limit,SHYT_DM_PAGE,0,0,&reserved)!=SHYT_DM_OK || reserved)) return 3;
        if (bb_singleton_arena_v528(&pool,&good,obj,sizeof obj,16,1120,objva,va,bytes,align,&out)!=BB_ARENA_READY) return 4;
        if (out.offset!=(i?align:0) || !out.storage || get(obj+1120)!=va ||
            get(obj+1128)!=out.offset || get(obj+1136)!=bytes ||
            get(obj+24)!=va+16 || get((unsigned char *)out.storage+8)!=((va+bytes-32)|2) ||
            obj[0]!=0xa5 || obj[1199]!=0xa5) return 5;
        if (shyt_dm_release(&pool,out.offset,bytes)!=SHYT_DM_OK ||
            (i && shyt_dm_release(&pool,reserved,SHYT_DM_PAGE)!=SHYT_DM_OK) || pool.count) return 6;
    }
    return 0;
}
