/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v487.h"
int main(void) {
    unsigned char data[8]={1,2,3,4,5,6,7,8};
    struct bb_region_v478 m={512,sizeof data,data};
    struct bb_input_v487 in={.rdi=512,.flags=0x8d5};
    struct bb_result_v484 out;
    if(bb_dispatch_v487(100,&in,NULL,&out)!=BB_OK_V487 || out.rax!=42) return 1;
    for(uint64_t a=108;a<=124;a+=8) {
        if(bb_dispatch_v487(a,&in,&m,&out)!=BB_OK_V487 || out.rax!=UINT64_C(0x0807060504030201) ||
            out.flags!=in.flags || out.flags_valid!=0x8d5) return 2;
    }
    ++in.rdi;
    out=(struct bb_result_v484){1,2,3};
    if(bb_dispatch_v487(124,&in,&m,&out)!=BB_READ_DENIED_V487 ||
       bb_dispatch_v487(108,&in,NULL,&out)!=BB_READ_DENIED_V487 ||
       bb_dispatch_v487(132,&in,&m,&out)!=BB_MISS_V487 ||
       bb_dispatch_v487(140,&in,&m,&out)!=BB_MISS_V487 ||
       bb_dispatch_v487(100,NULL,&m,&out)!=BB_MISS_V487) return 3;
    return out.rax!=1 || out.flags!=2 || out.flags_valid!=3;
}
