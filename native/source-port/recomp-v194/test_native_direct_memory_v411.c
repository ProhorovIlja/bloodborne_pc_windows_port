/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_direct_memory_host_v411.h"
#include <stdio.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"FAIL %d\n",__LINE__);return 1;} }while(0)
static int fail_unmap(void *ctx,void *ptr,uint64_t len) {
    (void)ctx; (void)ptr; (void)len;
    return 0;
}
static void *fail_map(void *ctx,uint64_t off,uint64_t len,uint64_t align,int type,unsigned prot) {
    (void)ctx; (void)off; (void)len; (void)align; (void)type; (void)prot;
    return NULL;
}
int main(void) {
    const uint64_t page=SHYT_DM_PAGE;
    const ShytDmBackend cpu={NULL,shyt_dm_cpu_map,shyt_dm_cpu_unmap};
    const ShytDmBackend failure={NULL,fail_map,fail_unmap};
    ShytDmPool pool={0};
    uint64_t off=777;
    void *mapped=NULL;
    CHECK(shyt_dm_init(&pool,8*page));
    CHECK(!shyt_dm_init(&pool,8*page));
    CHECK(shyt_dm_allocate(&pool,-1,8*page,page,0,0,&off)==SHYT_DM_INVALID && off==777);
    CHECK(shyt_dm_allocate(&pool,0,8*page,1,0,0,&off)==SHYT_DM_INVALID && off==777);
    CHECK(shyt_dm_allocate(&pool,1,8*page,2*page,3*page,3,&off)==SHYT_DM_OK && off==3*page);
    CHECK(shyt_dm_allocate(&pool,0,8*page,page,0,0,&off)==SHYT_DM_OK && off==0);
    CHECK(shyt_dm_allocate(&pool,3*page,5*page,page,0,0,&off)==SHYT_DM_NO_SPACE && off==0);
    CHECK(shyt_dm_map(&pool,&cpu,3*page,2*page,3*page,3,16,&mapped)==SHYT_DM_UNSUPPORTED);
    CHECK(shyt_dm_map(&pool,&cpu,3*page,2*page,3*page,0x33,0,&mapped)==SHYT_DM_UNSUPPORTED);
    CHECK(shyt_dm_map(&pool,&failure,3*page,2*page,3*page,3,0,&mapped)==SHYT_DM_BACKEND_FAILED && !mapped);
    CHECK(shyt_dm_map(&pool,&cpu,3*page,2*page,3*page,3,0,&mapped)==SHYT_DM_OK);
    CHECK((uintptr_t)mapped%(3*page)==0);
    unsigned char *bytes=mapped;
    for(size_t i=0;i<2*page;i++)CHECK(bytes[i]==0);
    bytes[0]=77; bytes[2*page-1]=21;
    CHECK(shyt_dm_map(&pool,&cpu,3*page,2*page,0,3,0,&mapped)==SHYT_DM_UNSUPPORTED && mapped==bytes);
    CHECK(shyt_dm_release(&pool,&cpu,3*page,page)==SHYT_DM_UNSUPPORTED);
    CHECK(shyt_dm_release(&pool,&failure,3*page,2*page)==SHYT_DM_BACKEND_FAILED);
    CHECK(pool.count==2 && bytes[0]==77 && bytes[2*page-1]==21);
    CHECK(shyt_dm_release(&pool,&cpu,3*page,2*page)==SHYT_DM_OK);
    CHECK(shyt_dm_allocate(&pool,3*page,8*page,2*page,3*page,3,&off)==SHYT_DM_OK && off==3*page);
    CHECK(shyt_dm_release(&pool,&cpu,off,2*page)==SHYT_DM_OK);
    CHECK(shyt_dm_release(&pool,&cpu,0,page)==SHYT_DM_OK && pool.count==0);
    ShytDmPool full={0};
    CHECK(shyt_dm_init(&full,(SHYT_DM_MAX+1)*page));
    for(size_t i=0;i<SHYT_DM_MAX;i++)
        CHECK(shyt_dm_allocate(&full,0,(SHYT_DM_MAX+1)*page,page,0,0,&off)==SHYT_DM_OK && off==i*page);
    CHECK(shyt_dm_allocate(&full,0,(SHYT_DM_MAX+1)*page,page,0,0,&off)==SHYT_DM_NO_SPACE);
    CHECK(shyt_dm_release(&full,&cpu,0,page)==SHYT_DM_OK);
    CHECK(shyt_dm_allocate(&full,0,(SHYT_DM_MAX+1)*page,page,0,0,&off)==SHYT_DM_OK && off==0);
    puts("NATIVE_V411_DIRECT_MEMORY_CORE_PASS");
    return 0;
}
