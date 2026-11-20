# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the nonzero restore arm through RET on Linux x86-64."""
import ctypes as c
from hashlib import sha256
from pathlib import Path
from random import Random
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

from test_resume_profile_return_v696 import State, U, P, W, N
from resume_switch_v697 import SHA


def run(path, cc):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected build')
    start = 0x25cdd02
    body = bytearray(blob[start+0x4000:0x25cde11+0x4000])
    for pc, op in ((0x25cdd61,b'\x4c\x89\xc2'),(0x25cdd9f,b'\x4c\x89\xca')):
        at = pc-start
        assert body[at:at+11] == bytes.fromhex('0f3189c048c1e2204809c2')
        body[at:at+11] = op+b'\x90'*8
    at = 0x25cddec-start
    assert body[at:at+3] == b'\x48\x8b\x05'
    body[at:at+7] = b'\x48\x89\xf8'+b'\x90'*4
    regs = ('rbx','rbp','r12','r13','r14','r15')
    asm = ['.text','.globl oracle','oracle:',*(f'push %{r}' for r in regs),
           'mov %rsp,%r11','mov %rcx,%r10','mov %rdi,%r12','mov %rdx,%rdi',
           'mov %rsi,%rsp','lea 192(%rsp),%rbp','mov (%r10),%eax',
           'mov 8(%r10),%rbx','mov 32(%r10),%r13','mov 48(%r10),%r15',
           '.byte '+','.join(map(str,body)), 'mov $2,%edx','jmp save',
           '.globl land','land:','mov $1,%edx','save:', 'mov %rax,(%r10)',
           *(f'mov %{r},{i*8}(%r10)' for i,r in enumerate(regs,1)),
           'mov %edx,%eax','mov %r11,%rsp',*(f'pop %{r}' for r in reversed(regs)),
           'ret','.section .note.GNU-stack,"",@progbits']
    bridge = '''#include "resume_restore_v700.h"
int step(struct bb_profile_state696 *s, uint32_t v, unsigned char *vm, size_t vs,
    const unsigned char *t, unsigned char *a, unsigned char *b, uint64_t x,
    uint64_t y, const uint64_t *f, size_t n, uint64_t g) {
    return bb_resume_restore700(s,v,vm,vs,t,0x68,a,0x4ec,b,0x4ec,x,y,f,n,g);
}
'''
    with TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp/'oracle.S').write_text('\n'.join(asm)+'\n')
        (tmp/'bridge.c').write_text(bridge)
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        '-I',str(Path(__file__).resolve().parent),'oracle.S','bridge.c',
                        '-o','test.so'],cwd=tmp,check=True)
        lib=c.CDLL(str(tmp/'test.so'))
        lib.oracle.argtypes=P,P,P,P,U,U
        lib.step.argtypes=P,W,P,N,P,P,P,U,U,P,N,U
        land=c.cast(lib.land,P).value
        rng=Random(700)
        for i in range(4096):
            vm,t,a,b=[c.create_string_buffer(rng.randbytes(n),n) for n in (0xc8,0x68,0x4ec,0x4ec)]
            if i&2:
                b=a
            if i&4:
                struct.pack_into('<I',a,0x4e8,0xffffffff)
            struct.pack_into('<QQ',vm,0x10,c.addressof(a),0)
            struct.pack_into('<Q',vm,0x90,c.addressof(t))
            v2,a2=[c.create_string_buffer(x.raw,len(x)) for x in (vm,a)]
            b2=a2 if b is a else c.create_string_buffer(b.raw,len(b))
            f=(U*26)(*(rng.getrandbits(64) for _ in range(26)))
            f[25]=land
            g=U(f[18]^(i&1))
            val=(1,42,0xffffffff,0x80000000)[(i>>3)%4]
            nv=(11,c.addressof(f)+192,c.addressof(vm),rng.getrandbits(64),99,c.addressof(b))
            out=(U*7)(val,*nv)
            x,y=rng.getrandbits(64),rng.getrandbits(64)
            s=State(0x25cdd02,77,(U*6)(*nv),99)
            before=bytes(s),v2.raw,a2.raw,b2.raw
            args=c.byref(s),val,v2,len(v2),t,a2,b2,x,y,f,26,g.value
            assert not lib.step(args[0],0,*args[2:])
            assert not lib.step(*args[:3],0xc7,*args[4:])
            assert not lib.step(*args[:-2],25,g.value)
            assert (bytes(s),v2.raw,a2.raw,b2.raw)==before
            expect=lib.oracle(vm,f,c.byref(g),out,x,y)
            assert expect==1+(i&1) and lib.step(*args)==expect
            assert (s.rax,list(s.nv),v2.raw,a2.raw,b2.raw)==(out[0],list(out)[1:],vm.raw,a.raw,b.raw)
            assert (s.pc,s.used)==((land,26) if expect==1 else (0x2bbe4f8,0))
    print(f'{cc}: 4096 differential outcomes, 12288 rejected inputs')


if __name__=='__main__':
    run(Path(sys.argv[1]),sys.argv[2])
