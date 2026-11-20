# SPDX-License-Identifier: GPL-2.0-or-later
"""Lift the attested zero/retry dispatch table, not its destination blocks."""
import argparse
import ctypes as c
from hashlib import sha256
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory

SHA = '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7'
START, BIAS = 0xa30b95, 0x4000


def decode(code, pc, read, lo, hi):
    if (len(code) != 35 or code[:12] != bytes.fromhex('bf01000000418b45604883f8')
            or code[13:15] != b'\x0f\x87' or code[19:22] != b'\x48\x8d\x0d'
            or code[26:] != bytes.fromhex('486304814801c8ffe0')):
        raise ValueError('unrecognized bounded indirect jump')
    count = code[12] + 1
    default = pc+19+struct.unpack_from('<i', code, 15)[0]
    table = pc+26+struct.unpack_from('<i', code, 22)[0]
    if not 0 < count <= 128 or not lo <= table <= hi-count*4:
        raise ValueError('invalid switch table span')
    targets = tuple(table+d for d, in struct.iter_unpack('<i', read(table,count*4)))
    if len(targets) != count or any(not lo <= t < hi for t in (*targets,default)):
        raise ValueError('switch destination outside RX')
    return targets, default


def inspect(path):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unsupported build')
    off = struct.unpack_from('<Q', blob, 32)[0]
    count = struct.unpack_from('<H', blob, 56)[0]
    (rx,) = (p for p in struct.iter_unpack('<II6Q',blob[off:off+count*56]) if p[0]==1 and p[1]&1)
    if rx[2]-rx[3] != BIAS:
        raise ValueError('unexpected RX mapping')
    read = lambda pc, n: blob[pc+BIAS:pc+BIAS+n]
    code = read(START,35)
    targets, default = decode(code,START,read,rx[3],rx[3]+rx[5])
    return code, targets, default


def emit(targets, default):
    cases = ', '.join(hex(t) for t in targets)
    return f'''#include <stdint.h>
#include <stddef.h>
#include <string.h>
int bb_zero_switch697(uint32_t value, const unsigned char *vm, size_t n,
                      uint64_t *next, uint32_t *edi) {{
    static const uint64_t cases[] = {{{cases}}};
    if (value || !vm || n < 0x64 || !next || !edi) return 0;
    uint32_t state;
    memcpy(&state,vm+0x60,4);
    *next = state < sizeof(cases)/sizeof(*cases) ? cases[state] : {default:#x};
    *edi = 1;
    return 1;
}}
'''


def check(code, targets, default, cc):
    # Retain the original dispatch opcodes. Relocate only Jcc, LEA, and the
    # table entries to observation stubs; original game targets are not run.
    asm = ['.text', '.globl oracle', 'oracle:', 'push %r13', 'mov %rdi,%r13',
           '.byte '+','.join(map(str,code[:15])), '.long fallback - . - 4',
           '.byte '+','.join(map(str,code[19:22])), '.long table - . - 4',
           '.byte '+','.join(map(str,code[26:])), 'table:']
    asm += [f'.long case{i} - table' for i in range(len(targets))]
    for i in range(len(targets)+1):
        label = f'case{i}' if i < len(targets) else 'fallback'
        asm += [f'{label}:', f'mov ${i},%eax', 'mov %edi,(%rsi)', 'pop %r13','ret']
    asm += ['.section .note.GNU-stack,"",@progbits']
    U, W, P = c.c_uint64, c.c_uint32, c.c_void_p
    with TemporaryDirectory(prefix='bb697-') as d:
        tmp = Path(d)
        (tmp/'oracle.S').write_text('\n'.join(asm)+'\n')
        (tmp/'lift.c').write_text(emit(targets,default))
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        'oracle.S','lift.c','-o','test.so'],cwd=tmp,check=True)
        lib = c.CDLL(str(tmp/'test.so'))
        lib.oracle.argtypes = P,P
        lib.bb_zero_switch697.argtypes = W,P,c.c_size_t,P,P
        rng = Random(697)
        vm = c.create_string_buffer(0x64)
        for i in range(8192):
            state = (i%16) if i%2==0 else rng.getrandbits(32)
            if i%32==1:
                state = (i//32)%7
            struct.pack_into('<I',vm,0x60,state)
            snapshot = vm.raw
            expected_edi, edi, nxt = W(),W(88),U(99)
            for result, size in ((1,0x64),(0,0x63)):
                assert not lib.bb_zero_switch697(result,vm,size,c.byref(nxt),c.byref(edi))
                assert (nxt.value,edi.value,vm.raw) == (99,88,snapshot)
            case = lib.oracle(vm,c.byref(expected_edi))
            assert case == min(state,len(targets))
            assert lib.bb_zero_switch697(0,vm,0x64,c.byref(nxt),c.byref(edi))
            assert (nxt.value,edi.value,vm.raw) == ((*targets,default)[case],expected_edi.value,snapshot)
    print(f'{cc}: 8192 dispatch comparisons, 16384 rejected inputs')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',action='append',default=[])
    p.add_argument('--extra-entries',type=Path,help='new private RVA list; do not publish')
    a = p.parse_args()
    code, targets, default = inspect(a.eboot)
    for cc in a.cc or ['cc']:
        check(code,targets,default,cc)
    if a.extra_entries:
        with a.extra_entries.open('x') as out:
            out.writelines(f'{pc:#x}\n' for pc in sorted(set((*targets,default))))
    print(f'{len(targets)} case entries plus one default; destination blocks not executed')
