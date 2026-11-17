/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_seed_v577.h"
#include "native_direct_memory_host_v411.h"
#include <stdio.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"V577 failure at %d\n",__LINE__); return 1; } } while (0)
static uint64_t word(const void *p) {
    uint64_t r;
    memcpy(&r,p,8);
    return r;
}
int main(void) {
    ShytDmPool pool={0};
    const ShytDmBackend backend={NULL,shyt_dm_cpu_map,shyt_dm_cpu_unmap};
    const uint64_t len=BB_ARENA_SIZE_V577, align=BB_ARENA_ALIGN_V577;
    void *mapped=NULL;
    uint64_t off=0, prior=99;
    _Alignas(8) unsigned char obj[BB_ARENA_OBJECT_V577+8],before[sizeof obj];
    memset(obj,0xa5,sizeof obj); memcpy(before,obj,sizeof obj);
    CHECK(shyt_dm_init(&pool,len+align));
    CHECK(shyt_dm_allocate(&pool,0,(int64_t)pool.limit,SHYT_DM_PAGE,0,0,&prior)==SHYT_DM_OK && prior==0);
    CHECK(shyt_dm_allocate(&pool,0,(int64_t)pool.limit,len,align,0,&off)==SHYT_DM_OK && off==align);
    CHECK(shyt_dm_map(&pool,&backend,off,len,align,3,0,&mapped)==SHYT_DM_OK);
    unsigned char *mem=mapped;
    const uint64_t a=(uintptr_t)mem, p=(uintptr_t)obj+0x40+26*16;
    CHECK(!bb_arena_seed_v577(obj,0x480,mem,(size_t)len,off));
    CHECK(!bb_arena_seed_v577(obj,sizeof obj,mem+1,(size_t)len,off));
    CHECK(!bb_arena_seed_v577(obj,sizeof obj,mem,(size_t)len,off+1));
    CHECK(!bb_arena_seed_v577(mem,sizeof obj,mem,(size_t)len,off));
    CHECK(!memcmp(before,obj,sizeof obj) && word(mem+8)==0);
    CHECK(bb_arena_seed_v577(obj,sizeof obj,mem,(size_t)len,off));
    CHECK(!memcmp(before,obj,0x28) && word(obj+0x480)==0 && obj[0x488]==0xa5);
    CHECK(word(obj+0x28)==(UINT64_C(1)<<26) && word(obj+0x470)==off && word(obj+0x478)==len);
    CHECK(word(obj+0x50)==(uintptr_t)obj+0x40 && word(obj+0x58)==(uintptr_t)obj+0x40);
    CHECK(word(obj+0x50+26*16)==a && word(obj+0x58+26*16)==a);
    CHECK(word(mem+8)==((a+len-32)|2) && word(mem+16)==p && word(mem+24)==p);
    CHECK(word(mem+len-32)==a && word(mem+len-24)==(a|1) && !word(mem+32));
    CHECK(shyt_dm_release(&pool,off,len)==SHYT_DM_OK);
    CHECK(shyt_dm_release(&pool,prior,SHYT_DM_PAGE)==SHYT_DM_OK && !pool.count);
    return 0;
}
