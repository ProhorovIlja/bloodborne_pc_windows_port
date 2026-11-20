# SPDX-License-Identifier: GPL-2.0-or-later
"""Linux x86-64 offline differential check; original bytes never leave the dump."""
import argparse
import ctypes as c
from hashlib import sha256
import mmap
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory

from ps4_ctor_order_v567 import SHA


def run(path, cc):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unsupported dump')
    thunk = 0x3ada00 + 0x4000
    if blob[thunk] != 0xe9:
        raise ValueError('unexpected cleanup thunk')
    start = thunk + 5 + struct.unpack_from('<i', blob, thunk+1)[0]
    code = blob[start:start+46]
    if code[-1] != 0xc3:
        raise ValueError('unexpected cleanup extent')
    page = mmap.mmap(-1, 4096, prot=3)
    addr = c.addressof(c.c_char.from_buffer(page))
    page[:len(code)] = code
    protect = c.CDLL(None).mprotect
    protect.argtypes = c.c_void_p, c.c_size_t, c.c_int
    if protect(addr, 4096, 5):
        raise OSError('cannot mark oracle RX')
    original = c.CFUNCTYPE(None, c.c_void_p)(addr)
    call = c.CFUNCTYPE(None, c.c_void_p)
    resolve = c.CFUNCTYPE(c.c_void_p, c.c_void_p, c.c_uint64, c.c_size_t)
    trace = []

    @call
    def callback(ptr):
        trace.append(c.string_at(ptr, 64))
        c.memset(ptr+8, 0xff, 8)
        c.memset(ptr+0x24, 0xff, 4)
        c.memset(ptr+0x30, 0xab, 1)

    cb = c.cast(callback, c.c_void_p).value
    table = (c.c_void_p*11)()
    table[10] = cb

    @resolve
    def registry(ctx, token, slot):
        return cb if token == c.addressof(table) and slot == 0x50 else None

    with TemporaryDirectory(prefix='bb687-') as d:
        src, so = Path(d)/'bridge.c', Path(d)/'bridge.so'
        src.write_text('#include "cleanup_v687.h"\nint run(void *p, size_t n, '
                       'bb_cleanup_resolve_v687 r) { return bb_cleanup_v687(p,n,0,r); }\n')
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
                        '-I',str(Path(__file__).resolve().parent),str(src),'-o',str(so)],check=True)
        native = c.CDLL(str(so)).run
        native.argtypes = c.c_void_p, c.c_size_t, resolve
        rng = Random(687)
        for i in range(4096):
            data = bytearray(rng.randbytes(64))
            struct.pack_into('<Q',data,8,c.addressof(table) if i % 2 else 0)
            a, b = map(c.create_string_buffer, (bytes(data), bytes(data)))
            trace.clear()
            original(a)
            before = trace[:]
            trace.clear()
            assert native(b,64,registry) == 1
            assert a.raw == b.raw and trace == before
            assert len(trace) == i % 2 and (not trace or trace[0] == data)
            snapshot = b.raw
            assert native(b,39,registry) == 0 and b.raw == snapshot
            struct.pack_into('<Q',data,8,1)
            bad = c.create_string_buffer(bytes(data))
            assert native(bad,64,registry) == 0 and bad.raw[:64] == data
    page.close()
    print(f'{cc}: 4096 original/native cleanup checks, 8192 invalid inputs rejected')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',default='cc')
    args = p.parse_args()
    run(args.eboot,args.cc)
