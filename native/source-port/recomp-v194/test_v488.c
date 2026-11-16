/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v487.h"
int main(void) {
    struct bb_result_v484 r={1,2,3};
    struct bb_input_v487 in={.rax=UINT64_C(0x7fffffffffffffff),.flags=0x202};
    if(bb_dispatch_v487(32,&in,0,&r)!=BB_OK_V487 ||
       r.rax!=UINT64_C(0x8000000000000000) || (r.flags&r.flags_valid)!=0x894) return 1;
    in.rax=UINT64_C(0xffffffff00000000);
    if(bb_dispatch_v487(48,&in,0,&r)!=BB_OK_V487 || r.rax!=1 ||
        (r.flags&r.flags_valid)!=0x11) return 2;
    in.rax=3; in.rdi=1;
    if(bb_dispatch_v487(64,&in,0,&r)!=BB_OK_V487 || r.rax!=1 || r.flags_valid!=0x8c5) return 3;
    in.rax=1;
    if(bb_dispatch_v487(80,&in,0,&r)!=BB_OK_V487 || r.rax!=1 ||
        (r.flags&r.flags_valid)!=0x44) return 4;
    in.rdi=UINT64_MAX; in.rsi=0;
    if(bb_dispatch_v487(96,&in,0,&r)!=BB_OK_V487 || r.rax!=UINT32_C(0xfffffffe)) return 5;
    if(bb_dispatch_v487(112,&in,0,&r)!=BB_OK_V487 || r.rax!=1 || r.flags_valid!=0x8d5) return 6;
    in.rax=1;
    if(bb_dispatch_v487(128,&in,0,&r)!=BB_OK_V487 || r.rax || (r.flags&r.flags_valid)!=0x55) return 7;
    for(uint64_t id=144;id<=160;id+=16)
        if(bb_dispatch_v487(id,&in,0,&r)!=BB_OK_V487 || r.rax!=2 || r.flags_valid!=0x8d5) return 9;
    if(bb_dispatch_v487(176,&in,0,&r)!=BB_MISS_V487 ||
       bb_dispatch_v487(192,&in,0,&r)!=BB_MISS_V487) return 10;
    r=(struct bb_result_v484){1,2,3};
    if(bb_dispatch_v487(33,&in,0,&r)!=BB_MISS_V487 || r.rax!=1 || r.flags!=2 || r.flags_valid!=3) return 8;
    return 0;
}
