# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline x86-64 caller-continuation check; keep generated code local."""
import argparse
import ctypes as c
from hashlib import sha256
import mmap
from pathlib import Path
from struct import unpack_from
import subprocess
from tempfile import TemporaryDirectory

from test_capture_v678 import (BIAS, END, ENTRY, RESUME, TAIL, SHA, State, U32,
                              U64, branch, emit_block, emit_branch,
                              emit_return, epilogue, oracle)

CALL = 0x230903d


def caller(blob):
    p = CALL + BIAS
    if blob[p] != 0xe8 or CALL+5+unpack_from('<i', blob, p+1)[0] != ENTRY:
        raise ValueError('unexpected caller')
    pc = CALL+5
    code = blob[p+5:p+13]
    if code[:4] != bytes.fromhex('84c00f84'):
        raise ValueError('unsupported caller continuation')
    return pc, pc+8+unpack_from('<i', code, 4)[0], pc+8, code


def test(path, cc):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable hash')
    pc, zero_pc, nonzero_pc, code = caller(blob)
    zero, nonzero = branch(blob, RESUME+BIAS, RESUME)
    if blob[nonzero+BIAS:nonzero+BIAS+3] != bytes.fromhex('31dbeb') or (
            nonzero+4+unpack_from('<b', blob, nonzero+BIAS+3)[0] != TAIL):
        raise ValueError('unsupported resume branch')
    tail = epilogue(blob[TAIL+BIAS:END+BIAS], TAIL)
    if not tail:
        raise ValueError('unsupported return')
    page, original, return_pc = oracle(blob)
    # Execute only the caller TEST/JZ as an independent oracle. Relocate
    # the taken target to a local return stub; leave the opcode unchanged.
    jump = b'\x48\x89\xf8' + code[:4] + (6).to_bytes(4,'little')
    jump += b'\xb8\x01\x00\x00\x00\xc3\x31\xc0\xc3'
    code_page = mmap.mmap(-1, 4096, prot=3)
    code_page[:len(jump)] = jump
    addr = c.addressof(c.c_char.from_buffer(code_page))
    protect = c.CDLL(None).mprotect
    protect.argtypes = (c.c_void_p, c.c_size_t, c.c_int)
    if protect(addr, 4096, 5):
        raise OSError('could not make caller oracle RX')
    expected = c.CFUNCTYPE(U32,U64)(addr)
    root = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix='bb679-') as d:
        tmp = Path(d)
        bridge = f'''#include "resume_chain_v677.h"
int bb_caller(uint64_t pc, uint64_t rax, uint64_t *next) {{
    if (!next || pc != {pc}) return 0;
    *next = (uint8_t)rax ? {nonzero_pc} : {zero_pc};
    return 1;
}}
int replay(struct bb_resume_state_v677 *s, uint32_t v, uint32_t *tls,
           uint64_t *f, size_t n) {{
    struct bb_resume_state_v677 next = *s;
    uint32_t staged = *tls;
    if (bb_resume_chain_v677(&next,v,&staged,(uintptr_t)tls,f,n)) return 0;
    if (!bb_caller(next.pc,next.rax,&next.pc)) return 0;
    *s = next; *tls = staged; return 1;
}}
'''
        sources = (emit_branch([(RESUME,zero,nonzero)]),
                   emit_block({nonzero:(0,TAIL,b'')}),emit_return({TAIL:tail}),bridge)
        files = []
        for i, src in enumerate(sources):
            f = tmp/f'unit{i}.c'
            f.write_text(src)
            files.append(str(f))
        so = tmp/'caller.so'
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
                        '-I',str(root),*files,'-o',str(so)],check=True)
        lib = c.CDLL(str(so))
        lib.bb_caller.argtypes = (U64,U64,c.POINTER(U64))
        lib.replay.argtypes = (c.POINTER(State),U32,c.POINTER(U32),c.POINTER(U64),c.c_size_t)
        for al in range(256):
            rax = 0xfedcba9876543200 | al
            dst = U64()
            assert lib.bb_caller(pc,rax,c.byref(dst)) == 1
            assert dst.value == (nonzero_pc if expected(rax) else zero_pc)
        for i in range(4096):
            capture, tls = (U64*18)(), U32(1)
            rv = (1,42,0xffffffff,0x80000000)[i%4]
            rax = original(i,i+5,c.byref(tls),capture,rv)
            assert capture[5] == return_pc and tls.value == 0
            tls.value = 1
            state = State(RESUME,0,(U64*6)(*capture[6:12]),0)
            snapshot = bytes(state)
            capture[5] = pc+1
            assert not lib.replay(c.byref(state),rv,c.byref(tls),capture,6)
            assert bytes(state)==snapshot and tls.value==1
            capture[5] = pc  # translate oracle wrapper address to retail call-site RVA
            assert lib.replay(c.byref(state),rv,c.byref(tls),capture,6)
            assert state.pc == (nonzero_pc if expected(rax) else zero_pc)
            assert state.rax==rax and state.consumed==6 and not tls.value
            assert list(state.nv)==list(capture[12:18])
    code_page.close()
    page.close()
    print(f'{cc}: 256 AL cases, 4096 captured-frame caller continuations and 4096 unknown-target rejections')


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',default='cc')
    a = p.parse_args()
    test(a.eboot,a.cc)
