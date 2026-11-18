# SPDX-License-Identifier: GPL-2.0-or-later
"""Host-only PNG parity and rollback tests; no proprietary assets required."""
import ctypes as c
from pathlib import Path
from random import Random
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

from test_png_decode_v705 import chunk, fixture


def check(cc):
    flags = subprocess.check_output(['pkg-config','--cflags','--libs','libpng'],text=True).split()
    root = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix='bb706-') as tmp:
        so = Path(tmp)/'test.so'
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        root/'png_rows_v706.c',root/'png_decode_v705.c',*flags,'-o',so],check=True)
        lib = c.CDLL(str(so))
        rows, rgba = lib.bb_png_rows706, lib.bb_png_rgba705
        P, N, U, UP = c.c_void_p,c.c_size_t,c.c_uint32,c.POINTER(c.c_uint32)
        rows.argtypes = P,N,P,N,N,c.c_uint,U,UP,UP
        rgba.argtypes = P,N,P,N,U,UP,UP
        rng = Random(706)
        changed = 0
        for i in range(2048):
            w,h = rng.randint(1,16),rng.randint(1,16)
            channels = 3+(i&1)
            src, expected, _ = fixture(rng,w,h,2 if channels==3 else 6)
            # gAMA 1.0: traditional raw rows must not be converted to sRGB.
            src = src[:33]+chunk(b'gAMA',struct.pack('>I',100000))+src[33:]
            row = w*channels
            stride = row+1+i%8
            size = (h-1)*stride+row
            out = c.create_string_buffer(b'\xa5'*size,size)
            a,b = U(17),U(19)
            corrupt = src[:-1]+bytes([src[-1]^1])
            for data,cap,pitch,ch in ((src,size-1,stride,channels),
                                      (src,size,row-1,channels),
                                      (src,size,stride,7-channels),
                                      (src[:-12],size,stride,channels),
                                      (corrupt,size,stride,channels)):
                assert not rows(data,len(data),out,cap,pitch,ch,16,c.byref(a),c.byref(b))
                assert out.raw==b'\xa5'*size and (a.value,b.value)==(17,19)
            assert rows(src,len(src),out,size,stride,channels,16,c.byref(a),c.byref(b))
            native = bytes(x for j,x in enumerate(expected) if channels==4 or j%4!=3)
            assert out.raw== (b'\xa5'*(stride-row)).join(native[y:y+row] for y in range(0,len(native),row))
            assert (a.value,b.value)==(w,h)
            old = c.create_string_buffer(len(expected))
            assert rgba(src,len(src),old,len(old),16,c.byref(a),c.byref(b))
            changed += old.raw!=expected
        assert changed>0
        print(f'{cc}: 2048 raw RGB/RGBA fixtures, 10240 rollback checks; simplified RGBA differs on {changed} gamma fixtures')


if __name__=='__main__':
    for cc in sys.argv[1:] or ['cc']:
        check(cc)
