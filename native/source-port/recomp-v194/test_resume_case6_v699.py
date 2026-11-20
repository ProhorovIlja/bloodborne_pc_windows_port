# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the zero-result switch case 6 through return with original x86-64 code offline."""
import ctypes as c
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
    assert len(targets) == 7 and targets[6] == 0xa31531
    blob = path.read_bytes()
    def read(pc, size):
        return blob[pc+0x4000:pc+0x4000+size]
    prefix = read(targets[6],10)
    assert prefix[:6] == bytes.fromhex('bf01000000e9')
    start = targets[6]+10+struct.unpack_from('<i',prefix,6)[0]
    code = read(start,default-start)
    # Relocate the four RIP-relative constant loads into the oracle's rodata.
    # Preserve every other instruction in the destination and shared tail.
    oracle_code = '.byte '+','.join(map(str,prefix[:5]))+'\n'
    constants, at = [], 0
    for i, (off, size) in enumerate(((13,8),(30,16),(38,16),(54,8))):
        addr = start+off+4+struct.unpack_from('<i',code,off)[0]
        oracle_code += '.byte '+','.join(map(str,code[at:off]))+'\n'
        oracle_code += f'.long k{i} - . - 4\n'
        constants += [f'k{i}:', '.byte '+','.join(map(str,read(addr,size)))]
        at = off+4
    oracle_code += '.byte '+','.join(map(str,code[at:]))+'\n'
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
'''+oracle_code+'''
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
.section .rodata
.balign 16
'''+'\n.balign 16\n'.join(constants)+'''
.section .note.GNU-stack,"",@progbits
'''
    bridge = '''#include "resume_case6_v699.h"
int step(struct bb_profile_state696 *s, uint32_t v, unsigned char *p, size_t z,
    const unsigned char *a, unsigned char *b, const uint32_t *t, uint64_t now,
    const uint64_t *f, size_t n, uint64_t g, const void *record) {
    return bb_case6_exit_v699(s,v,p,z,(const unsigned char *)record,0x20,a,0x58,b,0x520,t,now,f,n,g);
}
'''
    with TemporaryDirectory(prefix='bb699-') as d:
        tmp = Path(d)
        (tmp/'oracle.S').write_text(asm)
        (tmp/'bridge.c').write_text(bridge)
        (tmp/'dispatch.c').write_text(emit(targets,default))
        so = tmp/'test.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        '-I',str(Path(__file__).resolve().parent),'oracle.S','bridge.c','dispatch.c','-o',so],cwd=tmp,check=True)
        lib = c.CDLL(str(so))
        lib.reference.argtypes = P,U,P,P,P
        lib.step.argtypes = P,W,P,N,P,P,P,U,P,N,U,P
        land = c.cast(lib.land,P).value
        rng = Random(699)
        for i in range(4096):
            v, a, b, rec = [c.create_string_buffer(rng.randbytes(n),n) for n in (0x130,0x58,0x520,0x20)]
            tag, now = W(i&15),rng.getrandbits(64)
            struct.pack_into('<I',v,0x60,6)
            struct.pack_into('<Q',v,0x58,c.addressof(rec))
            scale = (0,1,-1,50,100,-100,2**31-1,-2**31)[i%8] if i%16<8 else rng.randrange(-2**31,2**31)
            clock = (0,1,2**63-1,2**63,2**64-1)[(i//16)%5] if i%32<16 else rng.getrandbits(64)
            struct.pack_into('<i',v,0x110,scale)
            struct.pack_into('<Q',rec,0x18,clock)
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
            assert not lib.step(*args,45,guard.value,rec)
            assert not lib.step(args[0],42,*args[2:],46,guard.value,rec)
            for case in (*range(6),7,0xffffffff):
                struct.pack_into('<I',v2,0x60,case)
                assert not lib.step(*args,46,guard.value,rec)
            struct.pack_into('<I',v2,0x60,6)
            assert (bytes(s),v2.raw,b2.raw) == saved
            expect = lib.reference(v,now,f,c.byref(guard),out)
            assert expect == 1+(i&1)
            assert lib.step(*args,46,guard.value,rec)==expect
            assert (v2.raw,b2.raw,s.rax)==(v.raw,b.raw,out[0])
            if expect==1:
                assert (s.pc,s.used,list(s.nv))==(land,46,list(out)[1:])
            else:
                assert (s.pc,s.used,list(s.nv))==(0x2bbe4f8,0,list(range(6)))
    print(f'{cc}: 2048 returns, 2048 guard failures, 40960 rejected inputs')


if __name__ == '__main__':
    run(Path(sys.argv[1]),sys.argv[2])
