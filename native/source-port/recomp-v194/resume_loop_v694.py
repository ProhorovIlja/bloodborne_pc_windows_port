# SPDX-License-Identifier: GPL-2.0-or-later
"""Lift the attested nonzero retry/exit block; no host setjmp is called here."""
import argparse
import ctypes as c
from hashlib import sha256
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory

from audit_setjmp_v673 import audit

PC = 0xa30b78
DIGEST = '27e4347de37fb5ecb5a7a013f9fadad129e8cbc014a0e16bfde9435d178ef4bf'


def scan(path):
    sites = []
    audit(path, resumes=sites)
    offset = dict(sites)[PC]
    blob = path.read_bytes()
    code = blob[offset:offset+29]
    if sha256(code).hexdigest() != DIGEST:
        raise ValueError('unexpected loop continuation')
    retry = PC+24+struct.unpack_from('<b', code, 23)[0]
    finish = PC+29+struct.unpack_from('<i', code, 25)[0]
    if retry != PC-8 or blob[offset-8:offset-4] != b'\x48\x89\xdf\xe8':
        raise ValueError('unexpected retry edge')
    return code, retry, finish


def emit(retry, finish):
    return '''#include <stddef.h>
#include <stdint.h>
#include <string.h>
/* 0: miss; 1: retry at original call edge; 2: enter profiling/exit block. */
int bb_loop694(uint64_t pc, uint32_t value, void *obj, size_t size,
               uint64_t *next, uint64_t *rax, uint64_t *rdi) {
    if (pc != %du || !value || !obj || size < 12 || !next || !rax || !rdi) return 0;
    uint32_t state, saved;
    unsigned char *p = obj;
    memcpy(&state,p,4);
    memcpy(&saved,p+8,4);
    memcpy(p+4,&saved,4);
    *rax=saved;
    *rdi=0;
    if (state==UINT32_C(0x80000000)) { *next=%du; return 1; }
    *next=%du;
    return 2;
}
''' % (PC,retry,finish)


def check(code, retry, finish, cc):
    # Execute the original block on the host. Only the external branch
    # displacements are redirected to observation stubs; the initial TEST
    # and JZ remain unchanged. The nonzero path never reaches the JZ target.
    raw = bytearray(code)
    raw[23] = 12
    raw[25:29] = bytes(4)
    oracle = '''.text
.globl reference
reference:
    push %%r13
    mov %%rdi,%%r13
    mov %%rsi,%%r10
    mov %%edx,%%eax
    .byte %s
    mov $2,%%ecx
    .byte 0xeb,5
retry:
    mov $1,%%ecx
record:
    mov %%rax,(%%r10)
    mov %%rdi,8(%%r10)
    mov %%ecx,%%eax
    pop %%r13
    ret
.section .note.GNU-stack,"",@progbits
''' % ','.join(map(str,raw))
    U, W, P = c.c_uint64, c.c_uint32, c.c_void_p
    with TemporaryDirectory(prefix='bb694-') as d:
        tmp = Path(d)
        (tmp/'loop.c').write_text(emit(retry,finish))
        (tmp/'oracle.S').write_text(oracle)
        so = tmp/'test.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
                        'loop.c','oracle.S','-o',so],cwd=tmp,check=True)
        lib = c.CDLL(str(so))
        lib.reference.argtypes = P,P,W
        step = lib.bb_loop694
        step.argtypes = U,W,P,c.c_size_t,P,P,P
        rng = Random(694)
        for i in range(4096):
            data = bytearray(rng.randbytes(32))
            if i % 2:
                struct.pack_into('<I',data,0,0x80000000)
            a, b = (c.create_string_buffer(bytes(data)) for _ in range(2))
            out = (U*2)()
            value = (1,0x80000000,0xffffffff,42)[i%4]
            status = lib.reference(a,out,value)
            assert status == (1 if i%2 else 2)
            dest, rax, rdi = U(9),U(10),U(11)
            result = tuple(map(c.byref,(dest,rax,rdi)))
            for pc, v, n in ((PC,0,32),(PC+1,value,32),(PC,value,11)):
                assert step(pc,v,b,n,*result)==0
                assert b.raw[:-1]==data and (dest.value,rax.value,rdi.value)==(9,10,11)
            assert step(PC,value,b,32,*result)==status
            assert a.raw==b.raw and tuple(out)==(rax.value,rdi.value)
            assert dest.value==(retry if status==1 else finish)
    print(f'{cc}: 4096 differential block checks and 12288 rejected inputs')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',action='append',default=[])
    a = p.parse_args()
    row = scan(a.eboot)
    for cc in a.cc or ['cc']:
        check(*row,cc)
