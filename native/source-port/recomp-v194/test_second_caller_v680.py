# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline differential test of the second caller's guarded return (Linux x86-64)."""
import argparse
import ctypes as c
from hashlib import sha256
import mmap
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory
from test_capture_v678 import BIAS, ENTRY, SHA, U64

CALL = 0x2307f65


def run(path, cc):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unsupported dump')
    i = CALL + BIAS
    assert blob[i] == 0xe8 and CALL+5+struct.unpack_from('<i',blob,i+1)[0] == ENTRY
    retail = bytearray(blob[i+5:i+42])
    assert retail[:3] == b'\x48\x8b\x1d' and retail[7:19].hex() == '4989de498b06483b45d07512'
    assert retail[19:].hex() == '4881c4280100005b415c415d415e415f5dc3'
    # Save the host stack; RDI holds the private frame, RSI the output.
    prefix = bytes.fromhex('555341544155415641574989e34889fc488daf50010000')
    page = mmap.mmap(-1,4096,prot=3)
    base = c.addressof(c.c_char.from_buffer(page))
    guard = U64()
    retail[3:7] = struct.pack('<i',256-len(prefix)-7)
    page[:len(prefix)+len(retail)] = prefix + retail
    # A bad canary reaches a test trap return, not the retail fatal import.
    restore = bytes.fromhex('4c89dc415f415e415d415c5b5dc3')
    bad = len(prefix)+len(retail)
    page[bad:bad+2+len(restore)] = b'\x31\xc0'+restore
    # The real RET reaches this host oracle landing pad. Snapshot its output.
    ok = bytes.fromhex('48890648895e084c8966104c896e184c8976204c897e2848896e30b801000000')+restore
    page[128:128+len(ok)] = ok
    page[256:264] = struct.pack('<Q',c.addressof(guard))
    protect = c.CDLL(None).mprotect
    protect.argtypes = (c.c_void_p,c.c_size_t,c.c_int)
    if protect(base,4096,5):
        raise OSError('could not set oracle page RX')
    reference = c.CFUNCTYPE(c.c_int,c.POINTER(U64),c.POINTER(U64))(base)
    with TemporaryDirectory(prefix='bb680-') as d:
        src, so = Path(d)/'bridge.c', Path(d)/'bridge.so'
        src.write_text('''#include <stddef.h>
#include <stdint.h>
int step(uint64_t pc, uint64_t guard, const uint64_t *f, size_t n,
         uint64_t out[8]) {
    if (!f || !out || pc != %d || n < 44 || f[36] != guard) return 0;
    out[0]=guard;
    for (size_t k=0; k<6; ++k) out[k+1]=f[37+k];
    out[7]=f[43];
    return 1;
}
''' % (CALL+5))
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',str(src),'-o',str(so)],check=True)
        step = c.CDLL(str(so)).step
        step.argtypes = (U64,U64,c.POINTER(U64),c.c_size_t,c.POINTER(U64))
        rng = Random(680)
        # Pre-pad the alternate stack so the oracle is not adjacent to a guard page.
        storage = (U64*128)()
        frame = c.cast(c.byref(storage,64*8),c.POINTER(U64))
        for trial in range(4096):
            for j in range(44):
                frame[j] = rng.getrandbits(64)
            guard.value = frame[36] ^ (0 if trial%2 == 0 else 1 << (trial%64))
            frame[43] = base+128
            original, native = (U64*8)(), (U64*8)()
            rc = reference(frame,original)
            assert rc == int(trial%2 == 0)
            assert step(CALL+5,guard.value,frame,44,native) == rc
            assert list(native) == list(original)[:7]+[frame[43] if rc else 0]
            before = bytes(native)
            assert not step(CALL+5,guard.value,frame,43,native)
            assert not step(CALL+6,guard.value,frame,44,native)
            assert bytes(native) == before
    page.close()
    print(f'{cc}: 4096 original/native guard and return comparisons, 8192 invalid-input checks')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--cc',default='cc')
    a = p.parse_args()
    run(a.eboot,a.cc)
