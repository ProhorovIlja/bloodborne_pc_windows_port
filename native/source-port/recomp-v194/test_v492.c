/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v492.h"
#include <string.h>
int main(void) {
    unsigned char bytes[12]={0}, saved[12];
    struct bb_write_region_v492 w={512,sizeof bytes,bytes};
    struct bb_region_v478 r={512,sizeof bytes,bytes};
    struct bb_input_v487 in={.rax=7,.rdi=512,.rsi=UINT64_C(0x0102030405060708),.flags=0x202};
    struct bb_result_v484 out;
    if(bb_dispatch_v492(200,&in,NULL,&w,&out)!=BB_OK_V492 ||
       out.rax!=7 || out.flags!=0x202 || out.flags_valid!=0x8d5 ||
       bytes[0] || bytes[1]!=8 || bytes[8]!=1 || bytes[9]) return 1;
    ++in.rdi;
    if(bb_dispatch_v492(116,&in,&r,NULL,&out)!=BB_OK_V492 || out.rax!=in.rsi ||
       bb_dispatch_v492(144,&in,NULL,NULL,&out)!=BB_OK_V492 || out.rax!=8 ||
       bb_dispatch_v492(100,&in,NULL,NULL,&out)!=BB_OK_V492 || out.rax!=42) return 2;
    memcpy(saved,bytes,sizeof bytes);
    out=(struct bb_result_v484){1,2,3};
    in.rdi=518;
    if(bb_dispatch_v492(200,&in,&r,&w,&out)!=BB_WRITE_DENIED_V492 ||
       bb_dispatch_v492(200,&in,&r,NULL,&out)!=BB_WRITE_DENIED_V492 ||
       bb_dispatch_v492(108,&in,&r,&w,&out)!=BB_READ_DENIED_V492 ||
       bb_dispatch_v492(201,&in,&r,&w,&out)!=BB_MISS_V492 ||
       bb_dispatch_v492(200,&in,&r,&w,NULL)!=BB_MISS_V492) return 3;
    return out.rax!=1 || out.flags!=2 || out.flags_valid!=3 || memcmp(saved,bytes,sizeof bytes);
}
