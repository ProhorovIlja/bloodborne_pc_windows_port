/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "continuation_v515.h"

static unsigned dispatch(uint64_t pc) {
    switch(pc) { case 3: return 37; case 5: return 59; default: return 0; }
}

int main(void) {
    struct bb_frame_v515 frames[]={{1,3,64},{2,5,48},{3,7,32}};
    struct bb_stack_v515 s={frames,3};
    struct bb_jump_v514 p={.rax=111};
    unsigned char record[72]={3};
    record[16]=64;
    if (bb_resume_v515(&s,4,record,72,1,0,0xffff,&p) || s.depth!=3 || p.rax!=111) return 1;
    record[0]=5;
    if (bb_resume_v515(&s,1,record,72,1,0,0xffff,&p) || s.depth!=3 || p.rax!=111) return 2;
    record[0]=3;
    frames[2]=frames[0];
    if (bb_resume_v515(&s,1,record,72,1,0,0xffff,&p) || s.depth!=3 || p.rax!=111) return 3;
    frames[2]=(struct bb_frame_v515){3,7,32};
    if (!bb_resume_v515(&s,1,record,72,0,0x20,0xffff,&p) || s.depth!=1 ||
        dispatch(p.rip)!=37 || p.rsp!=64 || p.rax!=1 || p.mxcsr!=0x20) return 4;
    record[0]=5; record[16]=48;
    if (bb_resume_v515(&s,2,record,72,1,0,0xffff,&p) || s.depth!=1 || p.rax!=1) return 5;
    record[0]=3; record[16]=64;
    if (!bb_resume_v515(&s,1,record,72,42,0,0xffff,&p) || p.rax!=42) return 6;
    return 0;
}
