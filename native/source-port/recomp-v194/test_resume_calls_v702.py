# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the caller through RET with host stubs for its three dependencies."""
import argparse
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
import subprocess
from tempfile import TemporaryDirectory

from resume_switch_v697 import SHA


def oracle(blob):
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected build')
    def read(pc, n):
        return blob[pc+0x4000:pc+0x4000+n]
    def rel(pc, n):
        return pc+n+unpack_from('<i',read(pc,n),n-4)[0]
    def raw(a,b):
        return '.byte '+','.join(map(str,read(a,b-a)))
    if [rel(p,n) for p,n in ((0x23a511b,5),(0x23a5120,7),(0x23a5132,5),
                           (0x23a5361,7),(0x23a536f,5),(0x23a53df,5))] != [
            0x3cdba0,0x53e7320,0x23a5359,0x53e3be0,0x69750,0x2bbe4f8]:
        raise ValueError('unexpected call graph')
    return '\n'.join(['.text','.globl oracle','oracle:',
        'push %rbp','push %rbx','push %r12','push %r13','push %r14','push %r15',
        'mov %rsp,saved(%rip)','mov %rdi,%r13','mov %rsi,%rsp',
        'lea 0x20e0(%rsp),%rbp','mov %edx,%eax',
        raw(0x23a510a,0x23a510c),'jz bad',raw(0x23a510e,0x23a511b),
        'call ref_restore','lea global_obj(%rip),%rax',raw(0x23a5127,0x23a5132),
        raw(0x23a5359,0x23a5361),'mov global_guard(%rip),%rbx',
        raw(0x23a5368,0x23a536f),'call ref_cleanup',raw(0x23a5374,0x23a5376),
        raw(0x23a53c4,0x23a53df),'mov $2,%edi','jmp record',
        '.globl land','land:','mov $1,%edi','record:',
        'mov %al,obs(%rip)','mov %rbx,obs+8(%rip)','mov %rbp,obs+16(%rip)',
        'mov %r12,obs+24(%rip)','mov %r13,obs+32(%rip)',
        'mov %r14,obs+40(%rip)','mov %r15,obs+48(%rip)','mov %edi,%eax',
        'mov saved(%rip),%rsp','pop %r15','pop %r14','pop %r13','pop %r12',
        'pop %rbx','pop %rbp','ret','bad: ud2',
        '.bss','.balign 8','saved: .zero 8','.section .note.GNU-stack,"",@progbits',''])


TEST = r'''
#include "resume_calls_v702.h"
#include <stdlib.h>
#include <stdio.h>
#define OK(x) do { if (!(x)) abort(); } while (0)
static unsigned char obj[0x1a1];
static _Alignas(16) uint64_t arena[8192];
static uint64_t *f=arena+4096;
static uint64_t g[2], *table, pass;
static unsigned logstep, fail_mode;
uint64_t *global_guard;
void *global_obj;
uint64_t obs[7];
extern int oracle(void *, uint64_t *, uint32_t);
extern void land(void);
struct vt { void (*pad[13])(void); void (*call)(void *, unsigned); };
void ref_restore(uint64_t arg, unsigned char *p, uint64_t z) {
    OK(!logstep++ && arg==f[5] && p==obj+16 && !z);
    global_obj=&table; obj[16]^=91;
}
static void ref_virtual(void *p, unsigned z) {
    OK(logstep++==1 && p==&table && !z && obj[0x1a0]==99);
    global_guard=&g[0];
}
void ref_cleanup(const uint64_t *p) {
    OK(logstep++==2 && p==f+526 && obj[0x1a0]==0);
    g[0]=pass; global_guard=&g[1]; obj[1]^=44;
}
static void restore(void *ctx, uint64_t a, unsigned char *b, uint64_t c) {
    (void)ctx; ref_restore(a,b,c);
}
static int invoke(void *ctx, unsigned slot, unsigned z) {
    (void)ctx; OK(slot==0x68 && global_obj==&table);
    if (fail_mode==1) return 0;
    ref_virtual(global_obj,z); return 1;
}
static const uint64_t *guard(void *ctx) {
    (void)ctx; return fail_mode==2 ? NULL : global_guard;
}
static void cleanup(void *ctx, const uint64_t *p) { (void)ctx; ref_cleanup(p); }
static void reset(void) {
    memset(obj,99,sizeof obj); logstep=0; global_obj=NULL; global_guard=NULL;
    g[0]=~pass; g[1]=~pass;
}
int main(void) {
    static struct vt v={.call=ref_virtual};
    table=(uint64_t *)&v;
    struct bb_calls702 calls={NULL,restore,invoke,guard,cleanup};
    for (unsigned i=0;i<4096;++i) {
        uint32_t val=(i&2)?0x80000000u:0xffffffffu;
        for (size_t j=0;j<1053;++j) f[j]=(uint64_t)i*0xabcdef1234ull+j;
        f[1053]=(uintptr_t)land; pass=f[1046]^(i&1);
        reset(); int expect=oracle(obj,f,val);
        OK(expect==1+(int)(i&1) && logstep==3);
        unsigned char result[sizeof obj]; memcpy(result,obj,sizeof obj);
        struct bb_state702 s={.pc=0x23a510a,.al=77,.used=9};
        reset();
        OK(bb_resume_calls702(&s,0,obj,sizeof obj,f,1054,&calls)==BB_MISS702);
        OK(bb_resume_calls702(&s,val,obj,sizeof obj-1,f,1054,&calls)==BB_MISS702);
        OK(bb_resume_calls702(&s,val,obj,sizeof obj,f,1053,&calls)==BB_MISS702);
        OK(!logstep && s.al==77 && s.used==9 && obj[16]==99 && obj[0x1a0]==99);
        OK(bb_resume_calls702(&s,val,obj,sizeof obj,f,1054,&calls)==(enum bb_result702)expect);
        OK(logstep==3 && !memcmp(obj,result,sizeof obj) && s.al==obs[0]);
        if (expect==1) OK(s.pc==f[1053] && s.used==1054 && !memcmp(s.nv,obs+1,sizeof s.nv));
        else OK(s.pc==0x2bbe4f8 && s.used==0);
        reset(); s.pc=0x23a510a; fail_mode=1;
        OK(bb_resume_calls702(&s,val,obj,sizeof obj,f,1054,&calls)==BB_STOP702);
        OK(logstep==1 && obj[16]==(99^91) && obj[0x1a0]==99);
        reset(); fail_mode=2;
        OK(bb_resume_calls702(&s,val,obj,sizeof obj,f,1054,&calls)==BB_STOP702);
        OK(logstep==2 && obj[0x1a0]==0); fail_mode=0;
    }
    puts("4096 differential outcomes, 12288 early misses, 8192 terminal misses");
}
'''


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',action='append',default=[])
    a=p.parse_args()
    asm=oracle(a.eboot.read_bytes())
    with TemporaryDirectory(prefix='bb702-') as d:
        root=Path(d)
        (root/'oracle.S').write_text(asm)
        (root/'test.c').write_text(TEST)
        for cc in a.cc or ['cc']:
            subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-no-pie','-I',
                str(Path(__file__).resolve().parent),'oracle.S','test.c','-o','test'],cwd=root,check=True)
            print(cc,subprocess.check_output([root/'test'],cwd=root,text=True,timeout=10).strip())
