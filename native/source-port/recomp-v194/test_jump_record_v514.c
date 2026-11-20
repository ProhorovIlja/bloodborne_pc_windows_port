/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "jump_record_v514.h"

int main(void) {
    unsigned char buf[72]={11,0,0,0,0,0,0,128};
    struct bb_jump_v514 p={0};
    for (unsigned i=1;i<8;++i) buf[i*8]=(unsigned char)(11+i);
    buf[64]=0x7f; buf[65]=3; buf[68]=0xc2; buf[69]=0x3f;
    for (unsigned i=0;i<64;++i) {
        if (!bb_jump_plan_v514(buf,sizeof buf,i,0x1f80|i,0xffff,&p)) return 1;
        if (p.rip!=UINT64_C(0x800000000000000b) || p.rbx!=12 || p.rsp!=13 ||
            p.rbp!=14 || p.r12!=15 || p.r13!=16 || p.r14!=17 || p.r15!=18 ||
            p.x87cw!=0x37f || p.mxcsr!=(0x3fc0|i) || p.rax!=(i?i:1)) return 2;
    }
    if (!bb_jump_plan_v514(buf,sizeof buf,UINT64_C(0x100000000),0x1f80,0xffff,&p) ||
        p.rax!=UINT64_C(0x100000000)) return 3;
    buf[71]=0x80;
    if (bb_jump_plan_v514(buf,sizeof buf,2,0x1f80,0xffff,&p) ||
        bb_jump_plan_v514(buf,71,2,0x1f80,0xffff,&p) ||
        bb_jump_plan_v514(0,72,2,0x1f80,0xffff,&p) || p.rax!=UINT64_C(0x100000000)) return 4;
    return 0;
}
