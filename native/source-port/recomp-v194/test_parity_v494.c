/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v493.h"
#include <stdio.h>
#include <string.h>
static uint64_t roll(uint64_t *s) {
    *s=*s*UINT64_C(6364136223846793005)+1;
    return *s;
}
int main(void) {
    uint64_t seed=493, compared=0;
    for(uint64_t id=0;id<=256;++id) {
        for(unsigned i=0;i<256;++i) {
            unsigned char a[32], b[32];
            for(size_t j=0;j<sizeof a;++j) a[j]=(unsigned char)(roll(&seed)>>56);
            memcpy(b,a,sizeof a);
            const struct bb_region_v478 ra={512,sizeof a,a}, rb={512,sizeof b,b};
            const struct bb_write_region_v492 wa={512,sizeof a,a}, wb={512,sizeof b,b};
            const struct bb_input_v487 in={roll(&seed),roll(&seed),roll(&seed),roll(&seed),
                                           504+i%48,roll(&seed)};
            struct bb_result_v484 x={1,2,3},y=x;
            const enum bb_status_v492 s=bb_dispatch_v492(id,&in,i&1?&ra:NULL,i&2?&wa:NULL,&x);
            const enum bb_status_v492 t=bb_dispatch_v493(id,&in,i&1?&rb:NULL,i&2?&wb:NULL,&y);
            if(s!=t||x.rax!=y.rax||x.flags!=y.flags||x.flags_valid!=y.flags_valid||
               memcmp(a,b,sizeof a)) {
                fprintf(stderr,"dispatch mismatch id=%llu case=%u\n",(unsigned long long)id,i);
                return 1;
            }
            ++compared;
        }
    }
    printf("V494_DISPATCH_PARITY %llu\n",(unsigned long long)compared);
    return 0;
}
