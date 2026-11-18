# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the game's retry block against a live host setjmp/longjmp loop.

Linux x86-64 test only. Original block bytes are read locally. The zero and
exit destinations are observation stubs, not implementations of the VM.
"""
import argparse
from hashlib import sha256
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from resume_switch_v697 import SHA

NATIVE = r'''
#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

int bb_live_retry701(jmp_buf *env, void *vm, size_t size,
                     int (*zero)(void *), void *ctx) {
    if (!env || !vm || size < 12 || !zero) return -1;
    unsigned char *p = vm;
    for (;;) {
        /* The save must stay in this frame, not in a helper that returns. */
        if (setjmp(*env) == 0) return zero(ctx);
        uint32_t mode, saved;
        memcpy(&saved,p+8,4);
        memcpy(p+4,&saved,4);
        memcpy(&mode,p,4);
        if (mode != UINT32_C(0x80000000)) return 2;
    }
}
'''

HARNESS = r'''
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct fixture {
    jmp_buf env;
    uint32_t vm[3], calls, limit, flags, seed, trace;
};
int bb_live_retry701(jmp_buf *, void *, size_t, int (*)(void *), void *);
int reference(jmp_buf *, void *, int (*)(void *), void *);
static int zero(void *arg) {
    struct fixture *f = arg;
    unsigned n = f->calls++;
    if (n > f->limit) abort();
    f->trace = f->trace * 33u + f->vm[1];
    if (n == f->limit && !(f->flags & 1)) return 1;
    f->vm[2] = f->seed ^ (n * UINT32_C(0x9e3779b9));
    f->vm[0] = n == f->limit ? 0 : UINT32_C(0x80000000);
    static const int values[] = {0, 1, -1, (-2147483647-1)};
    longjmp(f->env,values[(n+f->flags/2)%4]);
}
int main(void) {
    uint32_t saves = 0, jumps = 0;
    for (unsigned i=0;i<4096;++i) {
        struct fixture a = {.limit=i%32, .flags=i/32, .seed=i*919u};
        struct fixture b = {.limit=a.limit, .flags=a.flags, .seed=a.seed};
        if (bb_live_retry701(&b.env,b.vm,11,zero,&b) != -1 || b.calls) abort();
        int r = reference(&a.env,a.vm,zero,&a);
        int s = bb_live_retry701(&b.env,b.vm,sizeof b.vm,zero,&b);
        if (r != (a.flags & 1 ? 2 : 1) || r != s || a.calls != a.limit+1 ||
            a.calls != b.calls || a.trace != b.trace || memcmp(a.vm,b.vm,sizeof a.vm)) abort();
        saves += a.calls;
        jumps += a.limit + (a.flags & 1);
    }
    printf("4096 scenarios, %u live saves, %u nonlocal jumps per implementation\n",saves,jumps);
}
'''


def oracle(path):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable')
    off = 0xa30b78+0x4000
    block = blob[off:off+29]
    if block[:4] != b'\x85\xc0\x74\x19' or block[22:25] != b'\x74\xe0\xe9':
        raise ValueError('unexpected retry block')
    raw = lambda data: '.byte '+','.join(map(str,data))
    return '\n'.join(['.text','.globl reference','reference:',
        'push %rbx','push %r13','sub $24,%rsp', 'mov %rdi,%rbx','mov %rsi,%r13',
        'mov %rdx,(%rsp)','mov %rcx,8(%rsp)',
        'retry:','mov %rbx,%rdi','call _setjmp@PLT',raw(block[:3]),'.byte zero - . - 1',
        raw(block[4:23]),'.byte retry - . - 1','mov $2,%eax','jmp done',
        'zero:','mov 8(%rsp),%rdi','call *(%rsp)',
        'done:','add $24,%rsp','pop %r13','pop %rbx','ret',
        '.section .note.GNU-stack,"",@progbits',''])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',action='append',default=[])
    a = p.parse_args()
    asm = oracle(a.eboot)
    with TemporaryDirectory(prefix='bb701-') as d:
        root = Path(d)
        (root/'oracle.S').write_text(asm)
        (root/'native.c').write_text(NATIVE)
        (root/'test.c').write_text(HARNESS)
        for cc in a.cc or ['cc']:
            subprocess.run([cc,'-std=c11','-O3','-Wall','-Wextra','-Werror',
                            'oracle.S','native.c','test.c','-o','test'],cwd=root,check=True)
            print(cc, subprocess.check_output([root/'test'],cwd=root,text=True,timeout=10).strip())
