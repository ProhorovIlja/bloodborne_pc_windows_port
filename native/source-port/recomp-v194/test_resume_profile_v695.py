# SPDX-License-Identifier: GPL-2.0-or-later
"""Linux/x86-64 AVX differential test of the V694 exit accounting block."""
import ctypes as c
from hashlib import sha256
from pathlib import Path
from random import Random
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

SHA = '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7'


def run(path, cc):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected build')
    pc = 0xa34b90
    if blob[pc] != 0xe9:
        raise ValueError('unexpected V694 edge')
    start = pc+5+struct.unpack_from('<i',blob,pc+1)[0]
    code = bytearray(blob[start:0xa35507])
    if code[16:18] != b'\x0f\x31':
        raise ValueError('unexpected clock instruction')
    # Supply EDX:EAX in the wrapper instead of letting RDTSC vary.
    code[16:18] = b'\x90\x90'
    asm = '''.text
.globl reference
reference:
    push %rbx
    push %r13
    mov %rdi,%r13
    mov %rsi,%rax
    mov %rsi,%rdx
    shr $32,%rdx
    .byte '''+','.join(map(str,code))+'''
    vzeroupper
    pop %r13
    pop %rbx
    ret
.section .note.GNU-stack,"",@progbits
'''
    with TemporaryDirectory(prefix='bb695-') as d:
        tmp = Path(d)
        (tmp/'reference.S').write_text(asm)
        (tmp/'native.c').write_text('''#include "resume_profile_v695.h"
int step(unsigned char *v, size_t vn, const unsigned char *a, size_t an,
         unsigned char *p, size_t pn, const uint32_t *tag, uint64_t now) {
    return bb_profile_exit695(v,vn,a,an,p,pn,tag,now);
}
''')
        so = tmp/'compare.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        '-I',str(Path(__file__).resolve().parent),'reference.S','native.c',
                        '-o',so],cwd=tmp,check=True)
        lib = c.CDLL(str(so))
        p, z, u = c.c_void_p,c.c_size_t,c.c_uint64
        lib.reference.argtypes, lib.reference.restype = (p,u),None
        lib.step.argtypes = (p,z,p,z,p,z,p,u)
        rng = Random(695)
        for i in range(4096):
            v = c.create_string_buffer(rng.randbytes(0x50),0x50)
            a = c.create_string_buffer(rng.randbytes(0x58),0x58)
            s = c.create_string_buffer(rng.randbytes(0x520),0x520)
            t = c.c_uint32((rng.getrandbits(28)<<4) | (9 if i&1 else 8))
            x = rng.getrandbits(64)
            delta = (0,24,-24,48,24*(1<<31),rng.getrandbits(64))[(i//2)%6]
            struct.pack_into('<Q',v,0x48,c.addressof(a))
            struct.pack_into('<Q',a,0x10,c.addressof(s))
            struct.pack_into('<Q',a,0x28,(struct.unpack_from('<Q',a,0x18)[0]+delta)%(1<<64))
            struct.pack_into('<Q',a,0x50,c.addressof(t)+16)
            vn, sn = c.create_string_buffer(v.raw,len(v)),c.create_string_buffer(s.raw,len(s))
            snapshot = (vn.raw,sn.raw,a.raw)
            for vs,az,ss in ((0x4f,0x58,0x520),(0x50,0x57,0x520),(0x50,0x58,0x51f)):
                assert not lib.step(vn,vs,a,az,sn,ss,c.byref(t),x)
                assert (vn.raw,sn.raw,a.raw)==snapshot
            lib.reference(v,x)
            assert lib.step(vn,len(vn),a,len(a),sn,len(sn),c.byref(t),x)
            assert (vn.raw,sn.raw,a.raw)==(v.raw,s.raw,snapshot[2])
    print(f'{cc}: 4096 differential runs, 12288 short-span rejections')


if __name__ == '__main__':
    run(Path(sys.argv[1]),sys.argv[2])
