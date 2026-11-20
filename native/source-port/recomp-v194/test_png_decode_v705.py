# SPDX-License-Identifier: GPL-2.0-or-later
"""Attest the retail PNG helper fingerprints and exercise native decoding."""
import argparse
import ctypes as c
from hashlib import sha256
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory
import zlib


def attest(path):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7':
        raise ValueError('unexpected executable build')
    if b'libpng version 1.5.13' not in blob:
        raise ValueError('missing libpng version marker')
    for a, b, digest in (
        (0x3cdba0,0x3cdc9c,'ab37d86a7d7ee5dd7ffcfc32c40e1cf719a1fa69d2d19f6d96fcedcdd077ce79'),
        (0x3cc820,0x3cc87f,'fe94a809a518472bd0d8cd75be6406b83ecbf4727254a862f938bb7f3f31a780'),
        (0x3c7350,0x3c77f8,'940962679b274684e52953f6f781d854d0505b838c1134ffc3004c5c86c82f32'),
        (0x3cc980,0x3cc9a1,'b22349e28652ac1f2bdbeb3c5a05d66db71545b85ba4157dc14b8585c6384dfc'),
    ):
        if sha256(blob[a+0x4000:b+0x4000]).hexdigest() != digest:
            raise ValueError('unexpected PNG helper fingerprint')
    print('Attested libpng version marker and four retail helper ranges')


def chunk(kind, data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))


def fixture(rng, w, h, color):
    channels = {0:1,2:3,4:2,6:4}[color]
    rows, rgba = [], bytearray()
    for _ in range(h):
        row = rng.randbytes(w*channels)
        rows.append(b'\0'+row)
        for p in range(0,len(row),channels):
            x = row[p:p+channels]
            if color in (0,4):
                rgba.extend(x[:1]*3+(x[1:] if color==4 else b'\xff'))
            else:
                rgba.extend(x+(b'\xff' if color==2 else b''))
    header = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,color,0,0,0))
    tail = chunk(b'IEND',b'')
    return header+chunk(b'IDAT',zlib.compress(b''.join(rows)))+tail, rgba, header+chunk(b'IDAT',b'bad')+tail


def check(cc):
    flags = subprocess.check_output(['pkg-config','--cflags','--libs','libpng'],text=True).split()
    with TemporaryDirectory(prefix='bb705-') as d:
        so = Path(d)/'decode.so'
        subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
                        Path(__file__).with_name('png_decode_v705.c'),*flags,'-o',so],check=True)
        decode = c.CDLL(str(so)).bb_png_rgba705
        p, n, u = c.c_void_p, c.c_size_t, c.c_uint32
        decode.argtypes = (p,n,p,n,u,c.POINTER(u),c.POINTER(u))
        rng = Random(705)
        for i in range(2048):
            w,h = rng.randint(1,16),rng.randint(1,16)
            data, expected, bad = fixture(rng,w,h,(0,2,4,6)[i%4])
            size = len(expected)
            out = c.create_string_buffer(b'\xa5'*(size+16),size+16)
            a,b = u(17),u(19)
            for src, cap, limit in ((data,size-1,16),(data,size,max(w,h)-1),
                                    (data[:30],size,16),(bad,size,16)):
                assert not decode(src,len(src),out,cap,limit,c.byref(a),c.byref(b))
                assert out.raw == b'\xa5'*(size+16) and (a.value,b.value)==(17,19)
            assert decode(data,len(data),out,size,16,c.byref(a),c.byref(b))
            assert out.raw == expected+b'\xa5'*16 and (a.value,b.value)==(w,h)
        print(f'{cc}: 2048 exact RGBA fixtures, 8192 transactional failure checks')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--eboot',type=Path)
    p.add_argument('--cc',action='append',default=[])
    a = p.parse_args()
    if a.eboot:
        attest(a.eboot)
    for cc in a.cc or ['cc']:
        check(cc)
