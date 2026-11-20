/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "resume_chain_v677.h"
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>

struct fixture { uint64_t pc; size_t words; int zeroed; int slots[6]; };
static const struct fixture cases[]={
#include "cases677.inc"
};
static void check(const struct fixture *f, int result, unsigned seed) {
    const struct bb_resume_state_v677 before={f->pc,7,{17,19,23,29,31,37},99};
    struct bb_resume_state_v677 s=before;
    uint64_t frame[8];
    assert(f->words && f->words<=8);
    for (unsigned i=0;i<8;++i) frame[i]=UINT64_C(0x1234567812345678) ^ ((uint64_t)seed<<24) ^ i;
    uint32_t tls=0xaabbccdd;
    const uint64_t addr=(uintptr_t)&tls;
    assert(bb_resume_chain_v677(&s,(uint32_t)result,&tls,addr,frame,f->words-1)==BB_RESUME_EPILOGUE_V677);
    assert(tls==0xaabbccdd && s.pc==before.pc && s.rax==before.rax && s.consumed==before.consumed);
    for (unsigned i=0;i<6;++i) assert(s.nonvolatile[i]==before.nonvolatile[i]);
    assert(bb_resume_chain_v677(&s,(uint32_t)result,&tls,addr,frame,f->words)==BB_RESUME_OK_V677);
    assert(!tls && s.pc==frame[f->words-1] && s.consumed==f->words && s.rax==(f->zeroed<0 ? addr : (addr & ~UINT64_C(255))));
    for (unsigned i=0;i<6;++i) {
        assert(f->slots[i]<0 || (size_t)f->slots[i]<f->words-1);
        assert(s.nonvolatile[i]==(f->slots[i]>=0 ? frame[f->slots[i]] : (int)i==f->zeroed ? 0 : before.nonvolatile[i]));
    }
}
static void run(const struct fixture *f, int value, unsigned seed) {
    jmp_buf env;
    switch (setjmp(env)) {
    case 0: longjmp(env,value);
    case 1: assert(!value); check(f,1,seed); return;
    case 42: assert(value==42); check(f,42,seed); return;
    case -1: assert(value==-1); check(f,-1,seed); return;
    default: assert(0);
    }
}
int main(void) {
    for (size_t i=0;i<sizeof cases/sizeof *cases;++i)
        for (unsigned j=0;j<64;++j) { run(cases+i,0,j); run(cases+i,42,j); run(cases+i,-1,j); }
    printf("%zu full chain checks and short-frame rejections\n",192*sizeof cases/sizeof *cases);
}
