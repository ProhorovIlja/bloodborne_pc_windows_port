# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the zero-result switch default through return with original x86-64 code offline."""
import ctypes as c
from hashlib import sha256
from pathlib import Path
from random import Random
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

from resume_switch_v697 import inspect, emit

U, P, N, W = c.c_uint64, c.c_void_p, c.c_size_t, c.c_uint32


class State(c.Structure):
    _fields_ = [('pc', U), ('rax', U), ('nv', U*6), ('used', N)]


def run(path, cc):
    switch, targets, default = inspect(path)
    assert default == 0xa31464 and default not in targets
    blob = path.read_bytes()
    # In-range cases are not executed by this oracle. Jcc alone can reach
    # the accounting code; trap if a test feeds a different switch arm.
    code = switch[:15] + bytes((2,0,0,0)) + b'\x0f\x0b'
    body = bytearray(blob[0xa35464:0xa3552b])
    assert body[16:18] == b'\x0f\x31' and body[0xa3:0xa6] == b'\x48\x8b\x0d'
    body[16:18] = b'\x90\x90'  # wrapper injects EDX:EAX
    body[0xa3:0xaa] = b'\x4c\x89\xc9' + b'\x90'*4  # RCX = private guard pointer
    asm = '''.text
.globl reference
reference:
    push %rbp
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov %rsp,%r11
    mov %r8,%r10
    mov %rcx,%r9
    mov %rdx,%rsp
    lea 352(%rsp),%rbp
    mov %rdi,%r13
    .byte '''+','.join(map(str,code))+'''
    mov %rsi,%rax
    mov %rsi,%rdx
    shr $32,%rdx
    .byte '''+','.join(map(str,body))+'''
    mov $2,%edx
    jmp save
.globl land
land:
    mov $1,%edx
save:
    mov %rax,0(%r10)
    mov %rbx,8(%r10)
    mov %rbp,16(%r10)
    mov %r12,24(%r10)
    mov %r13,32(%r10)
    mov %r14,40(%r10)
    mov %r15,48(%r10)
    mov %edx,%eax
    vzeroupper
    mov %r11,%rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    pop %rbp
    ret
.section .note.GNU-stack,"",@progbits
'''
    bridge = '''#include "resume_switch_exit_v698.h"
int step(struct bb_profile_state696 *s, uint32_t v, unsigned char *p, size_t z,
    const unsigned char *a, unsigned char *b, const uint32_t *t, uint64_t now,
    const uint64_t *f, size_t n, uint64_t g) {
    return bb_zero_exit698(s,v,p,z,a,0x58,b,0x520,t,now,f,n,g);
}
'''
    with TemporaryDirectory(prefix='bb698-') as d:
        tmp = Path(d)
        (tmp/'oracle.S').write_text(asm)
        (tmp/'bridge.c').write_text(bridge)
        (tmp/'dispatch.c').write_text(emit(targets,default))
        so = tmp/'test.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        '-I',str(Path(__file__).resolve().parent),'oracle.S','bridge.c','dispatch.c','-o',so],cwd=tmp,check=True)
        lib = c.CDLL(str(so))
        lib.reference.argtypes = P,U,P,P,P
        lib.step.argtypes = P,W,P,N,P,P,P,U,P,N,U
        land = c.cast(lib.land,P).value
        rng = Random(698)
        for i in range(4096):
            v, a, b = [c.create_string_buffer(rng.randbytes(n),n) for n in (0x64,0x58,0x520)]
            tag, now = W(i&15),rng.getrandbits(64)
            struct.pack_into('<I',v,0x60,len(targets)+i)
            struct.pack_into('<Q',v,0x48,c.addressof(a))
            struct.pack_into('<Q',a,0x10,c.addressof(b))
            struct.pack_into('<Q',a,0x50,c.addressof(tag)+16)
            v2,b2 = c.create_string_buffer(v.raw,len(v)),c.create_string_buffer(b.raw,len(b))
            f = (U*46)(*(rng.getrandbits(64) for _ in range(46)))
            guard, out = U(f[38] ^ (i&1)), (U*7)()
            f[45] = land
            s = State(0xa30b95,99,(U*6)(*range(6)),99)
            saved = bytes(s),v2.raw,b2.raw
            args = c.byref(s),0,v2,len(v2),a,b2,c.byref(tag),now,f
            assert not lib.step(*args,45,guard.value)
            assert not lib.step(args[0],42,*args[2:],46,guard.value)
            for case in range(len(targets)):
                struct.pack_into('<I',v2,0x60,case)
                assert not lib.step(*args,46,guard.value)
            struct.pack_into('<I',v2,0x60,len(targets)+i)
            assert (bytes(s),v2.raw,b2.raw) == saved
            expect = lib.reference(v,now,f,c.byref(guard),out)
            assert expect == 1+(i&1)
            assert lib.step(*args,46,guard.value)==expect
            assert (v2.raw,b2.raw,s.rax)==(v.raw,b.raw,out[0])
            if expect==1:
                assert (s.pc,s.used,list(s.nv))==(land,46,list(out)[1:])
            else:
                assert (s.pc,s.used,list(s.nv))==(0x2bbe4f8,0,list(range(6)))
    print(f'{cc}: 2048 returns, 2048 guard failures, 36864 rejected inputs')


if __name__ == '__main__':
    run(Path(sys.argv[1]),sys.argv[2])
