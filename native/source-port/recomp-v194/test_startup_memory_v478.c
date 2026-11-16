/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <string.h>
#include "startup_memory_v478.h"
#include "native_startup_sret_v464.c"
#include "native_startup_getter_v465.c"
#include "native_data_v474.c"
#ifndef V478_PLAN
#define V478_PLAN "fixture_v478.h"
#endif
#include V478_PLAN
#define COUNT(a) (sizeof(a)/sizeof(*(a)))
static unsigned char data[DATA_SIZE], snapshot[DATA_SIZE];
int main(void) {
    unsigned char scratch[18], want[18];
    memset(scratch,0xa5,sizeof scratch);
    memset(want,0xa5,sizeof want);
    struct bb_memory_v478 memory={0};
    const struct bb_region_v478 rw={data_base,sizeof data,data}, stack={stack_base,16,scratch+1};
    if (bb_memory_bind_v478(&memory,rw,(struct bb_region_v478){data_base,16,scratch+1}) ||
        !bb_memory_bind_v478(&memory,rw,stack) || bb_memory_bind_v478(&memory,rw,stack)) return 1;
    if (!bb_data_init_v474(data,sizeof data,NULL,0,patches,COUNT(patches))) return 2;
    memcpy(snapshot,data,sizeof data);
    uint64_t value=99;
    if (bb_data_read64_v478(&memory,data_base+sizeof data-7,&value) || value!=99 ||
        bb_data_read64_v478(&memory,stack_base,&value) || value!=99) return 3;
    for (size_t i=0;i<COUNT(getters);++i) {
        const struct startup_getter_v465 *r=getters+i;
        if (!native_startup_getter_v465(r,r->site,r->receiver,bb_data_read64_v478,&memory,&value) || value!=fields[i]) return 4;
        const uint64_t unchanged=value;
        const size_t off=(size_t)(r->table+16u+8u*r->lane-data_base);
        data[off]^=1;
        if (native_startup_getter_v465(r,r->site,r->receiver,bb_data_read64_v478,&memory,&value) || value!=unchanged) return 5;
        data[off]^=1;
    }
    for (size_t i=0;i<2;++i) {
        uint64_t pos=stack_base+1+4*i;
        if (!native_startup_sret_v464(&sret,sret.sites[i],sret.receiver,pos,bb_data_read64_v478,
             bb_stack_write32_v478,&memory,&value) || value!=pos) return 6;
        for (unsigned j=0;j<4;++j) want[2+4*i+j]=(unsigned char)(sret.result>>(8*j));
        if (memcmp(want,scratch,sizeof want)) return 7;
    }
    const uint64_t invalid[]={data_base,stack_base-1,stack_base+13,UINT64_MAX};
    for (size_t i=0;i<COUNT(invalid);++i) {
        value=99;
        if (native_startup_sret_v464(&sret,sret.sites[0],sret.receiver,invalid[i],bb_data_read64_v478,
              bb_stack_write32_v478,&memory,&value) || value!=99) return 8;
    }
    return memcmp(data,snapshot,sizeof data) || memcmp(want,scratch,sizeof want) ? 9 : 0;
}
