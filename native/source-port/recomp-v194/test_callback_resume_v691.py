# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline x86-64 differential callback test and native frame checks."""
import ctypes as c
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

from audit_callback_resume_v691 import emit, scan

U, P = c.c_uint64, c.c_void_p
ERR = c.CFUNCTYPE(None, c.c_uint32)
FIN = c.CFUNCTYPE(None, P, U)
RE = c.CFUNCTYPE(P, P, U)
RF = c.CFUNCTYPE(P, P, U, c.c_size_t)


class State(c.Structure):
    _fields_ = [('pc', U), ('nv', U*6), ('rax', U), ('used', c.c_size_t)]


def run(path, cc):
    rows = scan(path)
    assert len(rows) == 2
    asm = ['.text']
    for i, (_, _, head, offset, tail) in enumerate(rows):
        asm += [f'.globl orig{i}', f'orig{i}:', 'push %rbx', 'push %r14',
                'sub $8,%rsp', 'mov %rdi,%rbx', 'mov %rsi,%r14',
                '.byte '+','.join(map(str,head)), f'.fill {offset-len(head)},1,0x90',
                '.byte '+','.join(map(str,tail)), 'add $8,%rsp', 'pop %r14', 'pop %rbx', 'ret']
    asm += ['.section .note.GNU-stack,"",@progbits']
    with TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d/'orig.S').write_text('\n'.join(asm)+'\n')
        (d/'gen.c').write_text(emit(rows))
        (d/'run.c').write_text('''#include "callback_resume_v691.h"
int run(struct bb_callback_state_v691 *s, unsigned val, void *p, size_t sz,
        bb_error_v691 (*e)(void *, uint64_t),
        bb_finish_v691 (*f)(void *,uint64_t,size_t), const uint64_t *frame, size_t n) {
    struct bb_calls_v691 calls={0,e,f};
    return bb_callback_resume_v691(s,val,p,sz,&calls,frame,n);
}
''')
        so = d/'a.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I',
                        str(Path(__file__).resolve().parent),d/'orig.S',d/'gen.c',d/'run.c','-o',so],check=True)
        lib = c.CDLL(str(so))
        native = lib.run
        native.argtypes = c.POINTER(State),c.c_uint32,P,c.c_size_t,RE,RF,c.POINTER(U),c.c_size_t
        trace = []
        obj = None

        @FIN
        def final(p, arg):
            trace.append(('final',U.from_address(p).value,arg))
            c.c_uint32.from_address(p+56).value ^= 0xf13579bd

        table = (P*2)(None,c.cast(final,P).value)
        table2 = (P*2)(None,c.cast(final,P).value)
        t1,t2 = c.addressof(table),c.addressof(table2)

        @ERR
        def error(status):
            trace.append(('error',status))
            struct.pack_into('<Q',obj,0,t2)

        cb = c.cast(error,P).value
        re = RE(lambda ctx,token: cb if token == cb else None)
        rf = RF(lambda ctx,token,slot: c.cast(final,P).value if slot==8 and token in (t1,t2) else None)
        absent = RF(lambda *args: None)
        for i,(pc,wide,*_) in enumerate(rows):
            orig = getattr(lib,f'orig{i}')
            orig.argtypes, orig.restype = (P,U),c.c_uint32
            pops = [0,2,3,4,5,1] if wide else [0,4,5,1]
            n = len(pops)+2
            for j in range(2048):
                initial = bytearray(60)
                struct.pack_into('<Q',initial,0,t1)
                struct.pack_into('<QI',initial,48,cb if j&1 else 0,(0x80000000 | j) if j&2 else 0)
                obj = c.create_string_buffer(bytes(initial))
                trace.clear()
                reference = orig(obj,0x123456789)
                expected = (obj.raw,trace[:])
                obj = c.create_string_buffer(bytes(initial))
                trace.clear()
                nv = [1,2,3,4,0x123456789,6]
                s = State(pc,(U*6)(*nv),99,100)
                snap = bytes(s)
                frame = (U*8)(*(0x100+j+k for k in range(8)))
                assert native(c.byref(s),42,obj,60,re,rf,frame,n-1)==0
                assert not trace and bytes(s)==snap and obj.raw[:-1]==initial
                assert native(c.byref(s),42,obj,60,re,rf,frame,n)==1
                for k,r in enumerate(pops,1):
                    nv[r]=frame[k]
                assert (obj.raw,trace)==expected
                assert (s.rax,s.pc,s.used,list(s.nv))==(reference,frame[n-1],n,nv)
                if j&3==3:
                    obj = c.create_string_buffer(bytes(initial))
                    trace.clear()
                    s = State.from_buffer_copy(snap)
                    assert native(c.byref(s),42,obj,60,re,absent,frame,n)==2
                    assert bytes(s)==snap and U.from_buffer(obj).value==t2 and len(trace)==1
    print(f'{cc}: 4096 differential callback and native frame checks, 4096 short frames, 1024 terminal misses')


if __name__ == '__main__':
    run(Path(sys.argv[1]),sys.argv[2])
