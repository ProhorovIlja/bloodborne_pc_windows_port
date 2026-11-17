# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline Linux/x86-64 oracle: give V677 a frame built by a retail prologue."""
import argparse
import ctypes as c
from hashlib import sha256
import mmap
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory

from audit_resume_branch_v674 import decode as branch, emit as emit_branch
from audit_resume_block_v675 import emit as emit_block
from audit_resume_return_v676 import decode as epilogue, emit as emit_return
from ps4_ctor_order_v567 import SHA

ENTRY, RESUME, TAIL, END = 0x23094c0, 0x23094fe, 0x230952d, 0x2309550
BIAS = 0x4000
U64 = c.c_uint64
U32 = c.c_uint32
REG = (3, 5, 12, 13, 14, 15)


class State(c.Structure):
    _fields_ = [('pc', U64), ('rax', U64), ('nv', U64*6), ('consumed', c.c_size_t)]


def oracle(blob):
    code = bytearray(blob[ENTRY+BIAS:END+BIAS])
    for pc in (0x23094d0, 0x23094e6, TAIL):
        at = pc-ENTRY
        assert code[at:at+9] == bytes.fromhex('64488b042500000000')
        assert code[at+9:at+12] == b'\x48\x03\x05'
        # RDX points to private TLS in this oracle; do not touch host FS.
        code[at:at+16] = b'\x48\x89\xd0' + b'\x90'*13
    at = RESUME-ENTRY-5
    assert code[at]==0xe8
    code[at+1:at+5] = struct.pack('<i',256-(at+5))
    # RCX: capture buffer. R8D: injected nonzero setjmp result. Read
    # above the stub's own return address, into the real game-built frame.
    stub = bytearray()
    for i in range(6):
        stub += bytes((0x48,0x8b,0x44,0x24,8+8*i,0x48,0x89,0x41,8*i))
    for i,r in enumerate(REG):
        stub += bytes((0x48 | (4 if r>=8 else 0),0x89,0x41|((r&7)<<3),48+8*i))
    stub += b'\x44\x89\xc0\xc3'
    # Wrapper sets a known return address and snapshots nonvolatiles after RET.
    wrapper = bytearray(b'\x48\x83\xec\x08\xe8'+struct.pack('<i',-512-9))
    for i,r in enumerate(REG):
        wrapper += bytes((0x48 | (4 if r>=8 else 0),0x89,0x81|((r&7)<<3))) + struct.pack("<i",96+8*i)
    wrapper += b'\x48\x83\xc4\x08\xc3'
    page = mmap.mmap(-1,4096,prot=3)
    base = c.addressof(c.c_char.from_buffer(page))
    page[:len(code)] = code
    page[256:256+len(stub)] = stub
    page[512:512+len(wrapper)] = wrapper
    protect = c.CDLL(None).mprotect
    protect.argtypes = (c.c_void_p,c.c_size_t,c.c_int)
    if protect(base,4096,5):
        raise OSError('could not set oracle page RX')
    fn = c.CFUNCTYPE(U64,U64,U64,c.POINTER(U32),c.POINTER(U64),U32)(base+512)
    return page,fn,base+521


def test(path, cc):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable hash')
    zero, nonzero = branch(blob,RESUME+BIAS,RESUME)
    assert blob[nonzero+BIAS:nonzero+BIAS+2]==b'\x31\xdb'
    assert blob[nonzero+BIAS+2]==0xeb
    assert nonzero+4+struct.unpack_from('<b',blob,nonzero+BIAS+3)[0]==TAIL
    end = epilogue(blob[TAIL+BIAS:END+BIAS],TAIL)
    assert end is not None and end[:3]==(0,1,[0,4,5,1])
    page, original, return_pc = oracle(blob)
    root = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix='bb678-') as directory:
        tmp = Path(directory)
        sources = [emit_branch([(RESUME,zero,nonzero)]),emit_block({nonzero:(0,TAIL,b'')}),
                   emit_return({TAIL:end}), '#include "resume_chain_v677.h"\n'
                   'int replay(struct bb_resume_state_v677 *s, uint32_t v, uint32_t *t, '
                   'const uint64_t *f, size_t n) { return bb_resume_chain_v677(s,v,t,(uintptr_t)t,f,n); }']
        inputs = []
        for i, source in enumerate(sources):
            out = tmp/f'part{i}.c'
            out.write_text(source)
            inputs.append(str(out))
        so = tmp/'replay.so'
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
                        '-I',str(root),*inputs,'-o',str(so)],check=True)
        replay = c.CDLL(str(so)).replay
        replay.argtypes = (c.POINTER(State),U32,c.POINTER(U32),c.POINTER(U64),c.c_size_t)
        rng = Random(678)
        for i in range(4096):
            obj, count = rng.getrandbits(64), rng.getrandbits(64)
            result = (1,42,0xffffffff,0x80000000)[i%4]
            words, tls = (U64*18)(), (U32*3)(17,23,29)
            cell = c.cast(c.byref(tls,4),c.POINTER(U32))
            ref = original(obj,count,cell,words,result)
            assert words[5]==return_pc and words[10]==count and words[11]==obj
            assert list(tls)==[17,0,29]
            tls[1] = 1
            state = State(RESUME,0,(U64*6)(*words[6:12]),0)
            assert replay(c.byref(state),result,cell,words,6)==0
            assert state.pc==return_pc and state.rax==ref and state.consumed==6
            assert list(state.nv)==list(words[12:18]) and list(tls)==[17,0,29]
    page.close()
    print(f'{cc}: 4096 native replays match a frame built by the original prologue')


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',default='cc')
    args = p.parse_args()
    test(args.eboot,args.cc)
