/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v497.h"
int main(void) {
    unsigned char bytes[16]={0};
    struct bb_region_v478 r={512,sizeof bytes,bytes};
    struct bb_write_region_v492 w={512,sizeof bytes,bytes};
    struct bb_input_v487 in={.rax=7,.rdi=512,.rsi=55,.flags=0x202};
    struct bb_result_v484 out;
    if(bb_dispatch_v497(256,&in,NULL,NULL,4096,&out)!=BB_OK_V492||
       out.rax!=4452||out.flags!=in.flags||out.flags_valid!=0x8d5)return 1;
    if(bb_dispatch_v497(256,&in,&r,&w,UINT64_MAX,&out)!=BB_ADDRESS_DENIED_V497||
       out.rax!=4452||out.flags!=in.flags||out.flags_valid!=0x8d5||bytes[1])return 2;
    if(bb_dispatch_v497(200,&in,&r,&w,4096,&out)!=BB_OK_V492||bytes[1]!=55||out.rax!=7)return 3;
    ++in.rdi;
    if(bb_dispatch_v497(116,&in,&r,&w,4096,&out)!=BB_OK_V492||out.rax!=55)return 4;
    if(bb_dispatch_v497(144,&in,&r,&w,4096,&out)!=BB_OK_V492||out.rax!=8)return 5;
    if(bb_dispatch_v497(100,&in,&r,&w,4096,&out)!=BB_OK_V492||out.rax!=42)return 6;
    if(bb_dispatch_v497(257,&in,&r,&w,4096,&out)!=BB_MISS_V492||out.rax!=42)return 7;
    return 0;
}
