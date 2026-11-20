# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare lifted cleanup tails with the original x86 instructions offline."""
import ctypes as c
from pathlib import Path
from random import Random
import subprocess
import sys
from tempfile import TemporaryDirectory

from cleanup_tail_v689 import emit, load


def run(path, cc):
    rows = load(path)
    asm = ['.text']
    for i, (_, _, (_, _, fail, code)) in enumerate(rows):
        restore = ['mov %r11,%rsp', 'pop %r14', 'pop %rbx', 'pop %rbp', 'ret']
        asm += [f'.globl ref{i}', f'ref{i}:', 'push %rbp', 'push %rbx', 'push %r14',
                'mov %rsp,%r11', 'mov %rsi,%r10', 'mov %rdi,%rsp',
                'lea 24(%rdi),%rbp', 'mov $77,%ebx', 'mov %rcx,%r14', 'mov %r8d,%eax']
        if fail is not None:
            asm += ['mov %rdx,%r14']
        asm += ['.byte '+','.join(map(str,code)), 'mov $2,%edx', f'jmp save{i}',
                f'.globl land{i}', f'land{i}:', 'mov $1,%edx', f'save{i}:',
                'mov %rbx,0(%r10)', 'mov %rbp,8(%r10)', 'mov %r14,16(%r10)',
                'mov %al,24(%r10)', 'mov %edx,%eax', *restore]
    asm += ['.section .note.GNU-stack,"",@progbits']
    U = c.c_uint64
    with TemporaryDirectory() as d:
        t = Path(d)
        (t/'tail.c').write_text(emit(rows))
        (t/'oracle.S').write_text('\n'.join(asm)+'\n')
        so = t/'test.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',str(t/'tail.c'),
                        str(t/'oracle.S'),'-o',str(so)],check=True)
        lib = c.CDLL(str(so))
        step = lib.bb_cleanup_tail
        step.argtypes = U,U,c.POINTER(U),c.c_size_t,c.c_size_t,c.POINTER(U),c.POINTER(c.c_uint8),c.POINTER(U),c.POINTER(c.c_size_t)
        rng = Random(689)
        for i,(pc,_,(skip,pops,fail,_)) in enumerate(rows):
            ref = getattr(lib,f'ref{i}')
            ref.argtypes = c.POINTER(U),c.POINTER(U),c.POINTER(U),U,c.c_uint32
            land = c.cast(getattr(lib,f'land{i}'),c.c_void_p).value
            n = skip+len(pops)+1
            for trial in range(512):
                f = (U*8)(*(rng.getrandbits(64) for _ in range(8)))
                f[n-1] = land
                guard, seed, al = U(f[0] ^ (trial%2)),rng.getrandbits(64),c.c_uint8(trial%256)
                before = (77,c.addressof(f)+24,0,0,c.addressof(guard) if fail is not None else seed,0)
                nv, out = (U*6)(*before),(U*4)()
                dst, consumed = U(1), c.c_size_t(9)
                args = nv,c.byref(al),c.byref(dst),c.byref(consumed)
                assert not step(pc,guard.value,f,n-1,3,*args)
                assert (tuple(nv),al.value,dst.value,consumed.value)==(before,trial%256,1,9)
                expect = ref(f,out,c.byref(guard),seed,al.value)
                assert expect == (2 if fail is not None and trial%2 else 1)
                assert step(pc,guard.value,f,8,3,*args) == expect
                assert (nv[0],nv[1],nv[4],al.value)==tuple(out)
                assert (dst.value,consumed.value)==((fail,0) if expect==2 else (land,n))
    print(f'{cc}: {len(rows)*512} original/native tail checks and short-frame rejections')


if __name__ == '__main__':
    run(Path(sys.argv[1]),sys.argv[2])
