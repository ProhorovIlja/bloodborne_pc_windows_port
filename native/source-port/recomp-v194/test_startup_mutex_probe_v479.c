/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "startup_mutex_probe_v479.h"
#include <string.h>
#ifdef V479_DIFFERENTIAL
extern uint64_t original_leaf(const unsigned char *,uint64_t);
#endif
int main(void) {
    unsigned char data[40], snapshot[40], stack[16]={0};
    struct bb_memory_v478 mem={0};
    if (!bb_memory_bind_v478(&mem,(struct bb_region_v478){4096,sizeof data,data},
         (struct bb_region_v478){8192,sizeof stack,stack})) return 1;
    memset(data,0x5a,sizeof data);
    unsigned count=0;
    for (uint64_t site=1;site<=4;++site) {
        for (unsigned i=0;i<256;++i) {
            for (unsigned j=0;j<8;++j) {
                data[16]=(unsigned char)i;
                memcpy(snapshot,data,sizeof data);
                const uint64_t seed=UINT64_C(0x8123456789abcdef)*(j+1)+i;
                uint64_t rax=seed, want=(seed & ~UINT64_C(255)) | i;
#ifdef V479_DIFFERENTIAL
                if (original_leaf(data,seed)!=want) return 2;
#endif
                if (!bb_mutex_probe_v479(&mem,site,site,4096,4096,&rax) || rax!=want ||
                    memcmp(snapshot,data,sizeof data)) return 3;
                ++count;
            }
        }
    }
    uint64_t rax=99;
    if (bb_mutex_probe_v479(&mem,1,2,4096,4096,&rax) ||
        bb_mutex_probe_v479(&mem,1,1,4097,4096,&rax) ||
        bb_mutex_probe_v479(&mem,1,1,8192,8192,&rax) ||
        bb_mutex_probe_v479(&mem,1,1,4120,4120,&rax) ||
        bb_mutex_probe_v479(&mem,1,1,UINT64_MAX,UINT64_MAX,&rax) || rax!=99) return 4;
    return count==8192 ? 0 : 5;
}
